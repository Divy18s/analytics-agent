"""Supervisor: profile -> plan -> code <-> execute(max 3) -> validate -> chart+story.

Handles 1..N CSVs + joins. Heuristic fallback = demo runs with no API key.
"""
from __future__ import annotations

import pandas as pd

from agents import llm
from tools.charts import pick_chart
from tools.profiler import profile_all
from tools.safe_exec import run_code

MAX_FIXES = 3


def _heuristic_plan(q: str, registry: dict) -> dict:
    import re
    ql, names = q.lower(), list(registry["datasets"])
    
    # Detect calculated expression e.g. revenue (quantity * unit_price * (1-discount))
    calc = None
    start = q.find("(")
    if start != -1:
        depth, end = 0, -1
        for idx in range(start, len(q)):
            if q[idx] == "(":
                depth += 1
            elif q[idx] == ")":
                depth -= 1
                if depth == 0:
                    end = idx
                    break
        if end != -1:
            expr = q[start + 1:end].strip()
            if any(op in expr for op in ("*", "/", "+", "-")):
                prefix = q[:start].strip().split()
                col = prefix[-1] if prefix else "calc_val"
                calc = {"col": col, "formula": expr}

    def _score(n: str) -> int:
        s = 0
        for c in registry["datasets"][n]["columns"]:
            cn = c["name"].lower()
            if cn in ql or any(part in ql for part in cn.split("_") if len(part) >= 4):
                s += 1
        return s

    ranked = sorted(names, key=lambda n: (-_score(n), names.index(n)))
    picked = [n for n in names if (n.lower().split(".")[0] in ql or n.lower().split(".")[0].replace("_", " ") in ql)]
    want_join = any(w in ql for w in ("join", "merge", "combin", " with ", " per customer", " per user", " and ")) or (calc is not None)
    
    if not picked:
        picked = [r for r in ranked if _score(r) > 0]
        if not picked:
            picked = [ranked[0]]
    if (len(picked) == 1 or calc is not None) and (want_join or len(picked) < 3):
        for r in ranked:
            if r not in picked and _score(r) > 0:
                picked.append(r)
                if len(picked) >= 3:
                    break

    joins = []
    if len(picked) > 1:
        # Build chained join sequence connecting picked datasets
        connected = [picked[0]]
        remaining = picked[1:]
        while remaining:
            found = False
            for cand in remaining:
                for base in connected:
                    k1 = f"{base}<->{cand}"
                    k2 = f"{cand}<->{base}"
                    shared = registry["join_candidates"].get(k1) or registry["join_candidates"].get(k2, [])
                    if shared:
                        joins.append({"left": base, "right": cand, "on": shared[0], "how": "left"})
                        connected.append(cand)
                        remaining.remove(cand)
                        found = True
                        break
                if found:
                    break
            if not found:
                break
        picked = connected

    prof = registry["datasets"][picked[0]]
    combo_cols = [c["name"] for p in picked for c in registry["datasets"][p]["columns"]]
    low = {c.lower(): c for c in combo_cols}
    
    # Exclude formula columns from candidate grouping dimensions
    calc_formula_cols = set(re.findall(r"\b[a-zA-Z_]\w*\b", calc["formula"].lower())) if calc else set()
    
    # Try finding dimension after 'by' or 'per'
    by_match = re.search(r"\b(?:by|per)\s+([a-zA-Z_]\w*)", ql)
    by_word = by_match.group(1).lower() if by_match else None
    
    g = None
    if by_word:
        candidates = [c for c in combo_cols if c.lower() not in calc_formula_cols and (by_word in c.lower() or c.lower() in by_word or by_word in c.lower().replace("_", " "))]
        candidates = sorted(candidates, key=lambda c: 1 if c.endswith("_id") or c == "id" else 0)
        if candidates:
            g = candidates[0]

    if not g:
        g = next((low[c] for c in low if (c in ql or c.replace("_", " ") in ql) and c not in calc_formula_cols), None)

    nums = [c for p in picked for c in registry["datasets"][p]["numeric"]]
    prioritized_nums = sorted(nums, key=lambda c: 1 if c.lower().endswith("_id") or c.lower() == "id" else 0)
    if calc:
        m = calc["col"]
    else:
        m = next((n for n in prioritized_nums if n.lower() in ql or n.lower().replace("_", " ") in ql), (prioritized_nums or [None])[0])

    if not g:
        non_calc_cats = [c for c in (prof["cats"] or combo_cols) if c.lower() not in calc_formula_cols]
        g = non_calc_cats[0] if non_calc_cats else (prof["cats"] or combo_cols)[0]

    # Parse simple where / filter conditions
    filt = None
    f_match = re.search(r"\b(?:where|filter)\s+([a-zA-Z_]\w*)\s+(is\s+)?(greater\s+than|>|less\s+than|<|equals?|==)\s+([0-9\.\w]+)", ql)
    if f_match:
        f_col = f_match.group(1)
        raw_op = f_match.group(3)
        val = f_match.group(4)
        if "greater" in raw_op or ">" in raw_op:
            f_op = ">"
        elif "less" in raw_op or "<" in raw_op:
            f_op = "<"
        else:
            f_op = "=="
        try:
            val = float(val) if "." in val else int(val)
        except Exception:
            pass
        filt = {"col": f_col, "op": f_op, "val": val}

    # Detect aggregation operator
    if any(w in ql for w in ("average", "avg", "mean")):
        agg = "mean"
    elif re.search(r"\bcount\b", ql) or any(w in ql for w in ("number of", "how many")):
        agg = "count"
    elif any(w in ql for w in ("min", "minimum", "lowest")):
        agg = "min"
    elif any(w in ql for w in ("max", "maximum", "highest")):
        agg = "max"
    else:
        agg = "sum"

    join_obj = joins if len(joins) > 1 else (joins[0] if len(joins) == 1 else None)
    return {"datasets": picked, "joins": joins if len(joins) > 1 else None,
            "join": joins[0] if len(joins) == 1 else None, "op": "groupby",
            "group_col": g, "metric_col": m, "calc": calc, "filter": filt, "agg": agg, "limit": 1000}


import json
import time
from pathlib import Path

HISTORY_FILE = Path(__file__).resolve().parent / "evals" / "user_query_history.jsonl"


def _save_query_log(record: dict) -> None:
    try:
        HISTORY_FILE.parent.mkdir(exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def get_query_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except Exception:
        return []


def _code(plan: dict) -> str:
    import re
    ds, j = plan.get("datasets", []), plan.get("joins") or plan.get("join")
    g, m, agg, lim = plan.get("group_col"), plan.get("metric_col"), plan.get("agg", "sum"), int(plan.get("limit", 1000) or 1000)
    filt = plan.get("filter")
    calc = plan.get("calc")
    if isinstance(j, list) and len(j) > 0:
        base = f"D['{j[0]['left']}']"
        for step in j:
            r_ds = step['right']
            on_col = step['on']
            h = step.get('how', 'left')
            base += f".merge(D['{r_ds}'], on='{on_col}', how='{h}')"
    elif isinstance(j, dict):
        l_ds = j['left']
        r_ds = j['right']
        on_col = j['on']
        h = j.get('how', 'left')
        base = f"D['{l_ds}'].merge(D['{r_ds}'], on='{on_col}', how='{h}')"
    else:
        base = f"D['{ds[0]}']" if ds else "pd.DataFrame()"

    calc_code = ""
    if calc and isinstance(calc, dict) and calc.get("col") and calc.get("formula"):
        c_col = calc["col"]
        c_form = calc["formula"]
        if "m[" in c_form:
            calc_code = f"m['{c_col}'] = {c_form}; "
        else:
            def _repl(match):
                t = match.group(0)
                if t in ("and", "or", "not", "True", "False", "None"):
                    return t
                return f"m['{t}']"
            c_py = re.sub(r"\b[a-zA-Z_]\w*\b", _repl, c_form)
            calc_code = f"m['{c_col}'] = {c_py}; "

    filter_code = ""
    if filt and isinstance(filt, dict) and filt.get("col"):
        f_col = filt['col']
        f_op = filt.get('op', '==')
        f_val = filt.get('val')
        if isinstance(f_val, str) and not f_val.isdigit():
            filter_code = f"m = m[m['{f_col}'] {f_op} '{f_val}']; "
        else:
            filter_code = f"m = m[m['{f_col}'] {f_op} {f_val}]; "

    if g and m:
        return (f"m = {base}; {calc_code}{filter_code}result = m.groupby('{g}')"
                f".agg(val=('{(m)}','{agg}')).reset_index()"
                f".sort_values('val', ascending=False).head({lim})")
    if g:
        return f"m = {base}; {calc_code}{filter_code}result = m['{g}'].value_counts().reset_index().head({lim})"
    return f"m = {base}; {calc_code}{filter_code}result = m.head({lim})"


def run_query(datasets: dict[str, pd.DataFrame], registry: dict, question: str, source: str = "ui") -> dict:
    trace = []
    p_llm = llm.plan(question, registry)
    plan = p_llm or _heuristic_plan(question, registry)
    trace.append(f"plan={plan} ({'llm' if p_llm else 'heuristic'})")
    code = llm.code(plan, question) or _code(plan)
    table, err = None, ""
    for i in range(1, MAX_FIXES + 1):
        try:
            table = run_code(datasets, code)
            if table.empty:
                err = "empty result"
                trace.append(f"attempt{i}: empty result")
                if i < MAX_FIXES:
                    fixed = llm.fix_code(plan, code, err, question)
                    code = fixed or _code(plan)
                continue
            trace.append(f"attempt{i}: ok rows={len(table)}")
            break
        except Exception as e:
            err = str(e)[:250]
            trace.append(f"attempt{i} error: {err}")
            if i < MAX_FIXES:
                fixed = llm.fix_code(plan, code, err, question)
                code = fixed or _code(plan)

    table = table if table is not None else pd.DataFrame()
    kind, fig = pick_chart(table)
    csv_head = table.head(10).to_csv(index=False) if not table.empty else ""
    if not table.empty:
        insight = llm.narrate(question, csv_head) or (
            f"Top: {table.iloc[0].tolist()} over {len(table)} groups. Chart: {kind}."
        )
    else:
        insight = f"No rows returned or error executing query: {err}" if err else "No rows returned."

    # Store query retrieval record ONLY for human UI queries (keeps automated tests separate)
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "plan": plan,
        "code": code,
        "mode": "llm" if p_llm else "heuristic",
        "rows": len(table),
        "columns": list(table.columns) if not table.empty else [],
        "sample": table.head(5).to_dict(orient="records") if not table.empty else [],
        "trace": trace,
        "error": err
    }
    if source == "ui":
        _save_query_log(record)

    return {"plan": plan, "code": code, "table": table, "fig": fig,
            "chart": kind, "insight": insight, "trace": trace, "error": err, "record": record}
