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

    TIME_FREQS = {"month": "M", "months": "M", "monthly": "M",
                  "week": "W", "weeks": "W", "weekly": "W",
                  "quarter": "Q", "quarters": "Q", "quarterly": "Q",
                  "year": "Y", "years": "Y", "yearly": "Y", "annual": "Y",
                  "day": "D", "days": "D", "daily": "D", "date": "D", "dates": "D"}
    TIME_LABEL = {"M": "month", "W": "week", "Q": "quarter", "Y": "year", "D": "date"}
    by_match_early = re.search(r"\b(?:by|per)\s+([a-zA-Z_]\w*)", ql)
    by_word_early = by_match_early.group(1).lower() if by_match_early else None
    
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

    # Detect semantic tables needed dynamically (without hardcoding table names)
    semantic_needed = []
    TIME_WORDS = ("month", "months", "monthly", "week", "weeks", "weekly",
                  "quarter", "quarters", "quarterly", "year", "years", "yearly", "annual",
                  "day", "days", "daily", "date", "dates")
    if any(w in ql for w in TIME_WORDS):
        for n in names:
            if registry["datasets"][n].get("time"):
                if n not in semantic_needed:
                    semantic_needed.append(n)
                break

    if any(w in ql for w in ("revenue", "sales", "turnover", "income", "money", "earnings", "spend")):
        direct_owner = None
        for n in names:
            for c in registry["datasets"][n]["columns"]:
                cn = c["name"].lower()
                if any(k in cn for k in ("revenue", "sales_amt", "total_amt", "amount", "amt")):
                    direct_owner = n
                    break
            if direct_owner:
                break
        if direct_owner:
            if direct_owner not in semantic_needed:
                semantic_needed.append(direct_owner)
        else:
            for n in names:
                cols = [c["name"].lower() for c in registry["datasets"][n]["columns"]]
                if any(any(k in c for k in ("price", "unit_price", "rate", "cost")) for c in cols):
                    if n not in semantic_needed:
                        semantic_needed.append(n)
                if any(any(k in c for k in ("quantity", "qty", "units", "items")) for c in cols):
                    if n not in semantic_needed:
                        semantic_needed.append(n)

    if not picked:
        picked = [r for r in ranked if _score(r) > 0]
        if not picked:
            if semantic_needed:
                picked = list(semantic_needed)
            else:
                picked = [ranked[0]]
    else:
        for s in semantic_needed:
            if s not in picked:
                picked.append(s)

    if (len(picked) == 1 or calc is not None) and (want_join or len(picked) < 3):
        for r in ranked:
            if r not in picked and _score(r) > 0:
                picked.append(r)
                if len(picked) >= 3:
                    break

    def _neighbors(node: str) -> list[tuple[str, str]]:
        out = []
        for key, cols in registry["join_candidates"].items():
            a, b = key.split("<->")
            if a == node:
                out.append((b, cols[0]))
            elif b == node:
                out.append((a, cols[0]))
        return out

    def _bridge(starts: list[str], target: str) -> list[dict] | None:
        from collections import deque
        prev: dict[str, tuple[str, str] | None] = {s: None for s in starts}
        dq = deque(starts)
        while dq:
            cur = dq.popleft()
            if cur == target:
                steps, node = [], cur
                while prev[node] is not None:
                    par, on = prev[node]
                    steps.append({"left": par, "right": node, "on": on, "how": "left"})
                    node = par
                return steps[::-1]
            for nb, on in _neighbors(cur):
                if nb not in prev:
                    prev[nb] = (cur, on)
                    dq.append(nb)
        return None

    joins = []
    if len(picked) > 1:
        # Connect picked datasets, bridging through intermediate tables when needed
        connected = [picked[0]]
        remaining = picked[1:]
        while remaining:
            best = None
            for cand in remaining:
                path = _bridge(connected, cand)
                if path is not None and (best is None or len(path) < len(best[1])):
                    best = (cand, path)
            if best is None:
                break
            cand, path = best
            for step in path:
                if step["right"] not in connected:
                    joins.append(step)
                    connected.append(step["right"])
            remaining.remove(cand)
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

    # time-derived grouping: "by month" -> derive period from date column
    date_group = None
    if not g and by_word in TIME_FREQS:
        freq = TIME_FREQS[by_word]
        tcol = next((c for p in picked for c in (registry["datasets"][p].get("time") or [])), None)
        if tcol is None:
            for n in names:
                tl = registry["datasets"][n].get("time") or []
                if tl:
                    tcol = tl[0]
                    break
        if tcol:
            date_group = {"col": tcol, "freq": freq}
            g = TIME_LABEL[freq]

    nums = [c for p in picked for c in registry["datasets"][p]["numeric"]]
    prioritized_nums = sorted(nums, key=lambda c: 1 if c.lower().endswith("_id") or c.lower() == "id" else 0)
    ql_nospace = ql.replace(" ", "").replace("_", "")
    def _metric_hit(n: str) -> bool:
        nn = n.lower()
        return (nn in ql or nn.replace("_", " ") in ql
                or nn.replace("_", "") in ql_nospace)
    if calc:
        m = calc["col"]
    else:
        m = next((n for n in prioritized_nums if _metric_hit(n)), (prioritized_nums or [None])[0])
        # money/revenue/sales alias -> direct col if exists, else dynamic calc from qty & price
        if any(w in ql for w in ("revenue", "sales", "turnover", "income", "money", "earnings")):
            direct_col = next((c for c in combo_cols if any(k in c.lower() for k in ("revenue", "sales_amt", "total_amt", "amount", "amt"))), None)
            if direct_col:
                m = direct_col
            else:
                q_col = next((c for c in combo_cols if any(k in c.lower() for k in ("qty", "quantity", "units", "items"))), None)
                p_col = next((c for c in combo_cols if any(k in c.lower() for k in ("unit_price", "price", "rate", "cost"))), None)
                d_col = next((c for c in combo_cols if any(k in c.lower() for k in ("discount", "disc"))), None)
                if q_col and p_col:
                    formula = f"{q_col} * {p_col}" + (f" * (1 - {d_col})" if d_col else "")
                    calc = {"col": "revenue", "formula": formula}
                    m = "revenue"

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

    # never sum/mean/min/max an id/key column when a real metric exists
    if (m is not None and (m.lower().endswith("_id") or m.lower() == "id")
            and agg in ("sum", "mean", "min", "max") and not calc):
        non_id = next((n for n in prioritized_nums if not (n.lower().endswith("_id") or n.lower() == "id")), None)
        if non_id is not None:
            m = non_id

    join_obj = joins if len(joins) > 1 else (joins[0] if len(joins) == 1 else None)
    return {"datasets": picked, "joins": joins if len(joins) > 1 else None,
            "join": joins[0] if len(joins) == 1 else None, "op": "groupby",
            "group_col": g, "metric_col": m, "calc": calc, "filter": filt,
            "date_group": date_group, "agg": agg, "limit": 1000}


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

    date_code = ""
    dg = plan.get("date_group")
    if dg and isinstance(dg, dict) and dg.get("col") and dg.get("freq"):
        date_code = (f"m['{g}'] = pd.to_datetime(m['{dg['col']}'])"
                     f".dt.to_period('{dg['freq']}').astype(str); ")

    if g and m:
        return (f"m = {base}; {calc_code}{filter_code}{date_code}result = m.groupby('{g}')"
                f".agg(val=('{(m)}','{agg}')).reset_index()"
                f".sort_values('val', ascending=False).head({lim})")
    if g:
        return f"m = {base}; {calc_code}{filter_code}result = m['{g}'].value_counts().reset_index().head({lim})"
    return f"m = {base}; {calc_code}{filter_code}result = m.head({lim})"


def _canonical_name(n: str, names: set[str]) -> str:
    if not n or not isinstance(n, str):
        return n
    if n in names:
        return n
    if f"{n}.csv" in names:
        return f"{n}.csv"
    n_low = n.lower()
    for k in names:
        if k.lower() == n_low or k.lower().rsplit(".", 1)[0] == n_low:
            return k
    return n


def _lookup_shared_keys(left: str, right: str, jc: dict) -> list[str]:
    k1 = f"{left}<->{right}"
    k2 = f"{right}<->{left}"
    if k1 in jc: return jc[k1]
    if k2 in jc: return jc[k2]
    l_base = left.rsplit(".", 1)[0].lower()
    r_base = right.rsplit(".", 1)[0].lower()
    for k, v in jc.items():
        if "<->" not in k: continue
        a, b = k.split("<->")
        a_base = a.rsplit(".", 1)[0].lower()
        b_base = b.rsplit(".", 1)[0].lower()
        if (a_base == l_base and b_base == r_base) or (a_base == r_base and b_base == l_base):
            return v
    return []


def normalize_plan(plan: dict, registry: dict) -> dict:
    if not isinstance(plan, dict):
        return plan
    plan = dict(plan)
    names = set(registry.get("datasets", {}))

    if "datasets" in plan and isinstance(plan["datasets"], list):
        plan["datasets"] = [_canonical_name(d, names) for d in plan["datasets"]]

    # Normalize joins
    j = plan.get("joins") or plan.get("join")
    if isinstance(j, dict):
        j["left"] = _canonical_name(j.get("left", ""), names)
        j["right"] = _canonical_name(j.get("right", ""), names)
        plan["joins"] = [j]
    elif isinstance(j, list):
        for step in j:
            if isinstance(step, dict):
                step["left"] = _canonical_name(step.get("left", ""), names)
                step["right"] = _canonical_name(step.get("right", ""), names)
        plan["joins"] = j

    # Auto-derive date_group if group_col is a time unit but date_group is missing
    g = plan.get("group_col")
    TIME_FREQS = {"month": "M", "months": "M", "monthly": "M",
                  "week": "W", "weeks": "W", "weekly": "W",
                  "quarter": "Q", "quarters": "Q", "quarterly": "Q",
                  "year": "Y", "years": "Y", "yearly": "Y", "annual": "Y",
                  "day": "D", "days": "D", "daily": "D", "date": "D"}
    if g and g.lower() in TIME_FREQS and not plan.get("date_group"):
        freq = TIME_FREQS[g.lower()]
        all_time = []
        for ds in plan.get("datasets", []):
            if ds in registry.get("datasets", {}):
                t_cols = registry["datasets"][ds].get("time") or []
                all_time.extend(t_cols)
                for c in registry["datasets"][ds].get("columns", []):
                    if any(k in c["name"].lower() for k in ("date", "time", "day", "month", "created", "timestamp", "dt")):
                        all_time.append(c["name"])
        if all_time:
            plan["date_group"] = {"col": all_time[0], "freq": freq}

    return plan


def validate_plan(plan: dict, registry: dict) -> tuple[bool, str]:
    """Generic structural check. No keywords: verifies datasets/cols/joins exist
    and the metric isn't a key column. Returns (ok, reason)."""
    if not isinstance(plan, dict):
        return False, "plan is not an object"
    names = set(registry.get("datasets", {}))
    ds = plan.get("datasets") or []
    if not ds:
        return False, "no datasets selected"
    for d in ds:
        if d not in names:
            return False, f"unknown dataset '{d}'"

    # all join steps must use known datasets + a real shared key
    steps: list[dict] = []
    j = plan.get("joins") or plan.get("join")
    if isinstance(j, dict):
        steps = [j]
    elif isinstance(j, list):
        steps = j
    jc = registry.get("join_candidates", {})
    joined = set(ds)
    for s in steps:
        if not isinstance(s, dict) or not all(k in s for k in ("left", "right", "on")):
            return False, f"malformed join step {s}"
        left, right, on_col = s["left"], s["right"], s["on"]
        shared = _lookup_shared_keys(left, right, jc)
        if on_col not in shared:
            return False, f"join key '{on_col}' not shared between {left} and {right}"
        joined |= {left, right}

    cols = {c["name"] for n in joined if n in names for c in registry["datasets"][n]["columns"]}
    time_cols = {t for n in joined if n in names for t in (registry["datasets"][n].get("time") or [])}
    for n in joined:
        if n in names:
            for c in registry["datasets"][n].get("columns", []):
                cn = c["name"].lower()
                if any(k in cn for k in ("date", "time", "day", "month", "year", "created", "timestamp", "dt")):
                    time_cols.add(c["name"])

    g, m = plan.get("group_col"), plan.get("metric_col")
    dg = plan.get("date_group")
    if dg:
        if not isinstance(dg, dict) or (dg.get("col") not in time_cols and dg.get("col") not in cols):
            return False, f"date_group col '{(dg or {}).get('col')}' is not a known date column"
    elif g and g not in cols and g.lower() not in ("month", "year", "week", "quarter", "day", "date"):
        return False, f"group col '{g}' not in {sorted(joined)}"

    calc = plan.get("calc")
    calc_cols = set()
    if calc:
        if not isinstance(calc, dict) or not calc.get("col") or not calc.get("formula"):
            return False, "malformed calc"
        import re as _re
        calc_cols = {w for w in _re.findall(r"\b[a-zA-Z_]\w*\b", calc["formula"])
                     if w not in ("and", "or", "not", "True", "False", "None", "m", "df", "pd", "np", "d", "round", "abs", "sum", "min", "max", "len")}
        low = {c.lower() for c in cols}
        unknown = {w for w in calc_cols if w.lower() not in low}
        if unknown:
            return False, f"calc uses unknown columns {sorted(unknown)}"
    if m and m not in cols and not (calc and m == calc.get("col")):
        return False, f"metric col '{m}' not in {sorted(joined)}"
    if (m and (m.lower().endswith("_id") or m.lower() == "id")
            and plan.get("agg", "sum") in ("sum", "mean", "min", "max")
            and not (calc and m == calc.get("col"))):
        return False, f"metric '{m}' is a key column, not a measure"
    return True, ""


def run_query(datasets: dict[str, pd.DataFrame], registry: dict, question: str, source: str = "ui") -> dict:
    trace = []
    plan, mode = None, "heuristic"

    p_llm = llm.plan(question, registry)
    if p_llm is not None:
        p_llm = normalize_plan(p_llm, registry)
        ok, reason = validate_plan(p_llm, registry)
        if ok:
            plan, mode = p_llm, "llm"
            trace.append("plan accepted (llm)")
        else:
            trace.append(f"llm plan rejected: {reason}")
            # one generic retry with the rejection as feedback (no keywords)
            p_retry = llm.plan(f"{question}\n[Your previous plan was invalid: {reason}. Fix it.]", registry)
            if p_retry is not None:
                p_retry = normalize_plan(p_retry, registry)
                ok2, reason2 = validate_plan(p_retry, registry)
                if ok2:
                    plan, mode = p_retry, "llm"
                    trace.append("retry plan accepted (llm)")
                else:
                    trace.append(f"retry rejected: {reason2}")
            elif llm.last_error:
                trace.append(f"retry llm error: {llm.last_error[:200]}")
    elif llm.last_error:
        trace.append(f"llm unavailable: {llm.last_error[:200]}")

    if plan is None:
        h = _heuristic_plan(question, registry)
        h = normalize_plan(h, registry)
        ok, reason = validate_plan(h, registry)
        if ok:
            plan, mode = h, "heuristic"
            trace.append(f"plan accepted ({mode})")
        else:
            trace.append(f"heuristic rejected: {reason}")
    if plan is None:
        plan = _heuristic_plan(question, registry)  # best-effort for audit
        mode = "failed"
    trace.append(f"plan={plan} ({mode})")
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
