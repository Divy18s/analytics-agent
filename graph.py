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
    ql, names = q.lower(), list(registry["datasets"])
    # pick datasets mentioned by name, else first (or first two if join words)
    # dataset-aware pick: score each file by column-name hits in the question
    def _score(n: str) -> int:
        return sum(1 for c in registry["datasets"][n]["columns"] if c["name"].lower() in ql)
    ranked = sorted(names, key=lambda n: (-_score(n), names.index(n)))
    picked = [n for n in names if n.lower().split(".")[0] in ql] or [ranked[0]]
    want_join = any(w in ql for w in ("join", "merge", "combin", " with ", " per customer", " per user"))
    if not picked:
        picked = names[:2] if (want_join and len(names) > 1) else [ranked[0]]
    # if question names columns from a second file, include it (join or switch)
    if len(picked) == 1 and ranked[0] != picked[0] and _score(ranked[0]) > 0:
        picked = [picked[0], ranked[0]] if want_join or _score(picked[0]) == 0 else [ranked[0]]
    join = None
    if len(picked) > 1:
        key = f"{picked[0]}<->{picked[1]}"
        shared = registry["join_candidates"].get(key) or registry["join_candidates"].get(f"{picked[1]}<->{picked[0]}", [])
        if shared:
            join = {"left": picked[0], "right": picked[1], "on": shared[0], "how": "left"}
        else:
            picked = picked[:1]
    prof = registry["datasets"][picked[0]]
    # search columns across picked files (not just the first) for group/metric hits
    combo_cols = [c["name"] for p in picked for c in registry["datasets"][p]["columns"]]
    low = {c.lower(): c for c in combo_cols}
    g = next((low[c] for c in low if c in ql), None)
    nums = [c for p in picked for c in registry["datasets"][p]["numeric"]]
    m = next((n for n in nums if n.lower() in ql), (nums or [None])[0])
    if not g:
        g = (prof["cats"] or combo_cols)[0]
    # ensure the primary file actually contains the group col; else switch/join
    def _has(ds: str, col: str | None) -> bool:
        return col is not None and col in [c["name"] for c in registry["datasets"][ds]["columns"]]
    if not _has(picked[0], g):
        owner = next((n for n in names if _has(n, g)), None)
        if owner:
            picked = [owner] if owner == picked[0] else ([picked[0], owner] if m and _has(picked[0], m) and not _has(owner, m) else [owner])
            if len(picked) == 2:
                key = f"{picked[0]}<->{picked[1]}"
                shared = registry["join_candidates"].get(key) or registry["join_candidates"].get(f"{picked[1]}<->{picked[0]}", [])
                join = {"left": picked[0], "right": picked[1], "on": shared[0], "how": "left"} if shared else None
                if not join:
                    picked = [owner]
    return {"datasets": picked, "join": join, "op": "groupby",
            "group_col": g, "metric_col": m, "agg": "sum", "limit": 20}


def _code(plan: dict) -> str:
    ds, j = plan["datasets"], plan.get("join")
    g, m, agg, lim = plan.get("group_col"), plan.get("metric_col"), plan.get("agg", "sum"), int(plan.get("limit", 20) or 20)
    base = f"D['{ds[0]}']" if not j else (
        f"D['{j['left']}'].merge(D['{j['right']}'], on='{j['on']}', how='{j['how']}')")
    if g and m:
        return (f"m = {base}; result = m.groupby('{g}')"
                f".agg(val=('{(m)}','{agg}')).reset_index()"
                f".sort_values('val', ascending=False).head({lim})")
    if g:
        return f"m = {base}; result = m['{g}'].value_counts().reset_index().head({lim})"
    return f"m = {base}; result = m.head({lim})"


def run_query(datasets: dict[str, pd.DataFrame], registry: dict, question: str) -> dict:
    trace = []
    p_llm = llm.plan(question, registry)
    plan = p_llm or _heuristic_plan(question, registry)
    trace.append(f"plan={plan} ({'llm' if p_llm else 'heuristic'})")
    code = llm.code(plan) or _code(plan)
    table, err = None, ""
    for i in range(1, MAX_FIXES + 1):
        try:
            table = run_code(datasets, code)
            if table.empty:
                err, code = "empty result", _code(plan)
                trace.append(f"attempt{i}: empty, retry heuristic")
                continue
            trace.append(f"attempt{i}: ok rows={len(table)}")
            break
        except Exception as e:
            err = str(e)[:250]
            trace.append(f"attempt{i} error: {err}")
            code = _code(plan)
    table = table if table is not None else pd.DataFrame()
    kind, fig = pick_chart(table)
    insight = llm.narrate(question, table.head(10).to_csv(index=False)) or (
        f"Top: {table.iloc[0].tolist()} over {len(table)} groups. Chart: {kind}."
        if len(table) else "No rows returned.")
    return {"plan": plan, "code": code, "table": table, "fig": fig,
            "chart": kind, "insight": insight, "trace": trace, "error": err}
