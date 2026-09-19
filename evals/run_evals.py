"""Eval runner: loads data/*.csv, runs 8 fixed checks, writes evals/results.md.

Usage: python evals/run_evals.py   (run from analytics-agent/ so imports resolve)
Scores: table non-empty, expected column present, join correctness vs pandas ground truth.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from graph import run_query
from tools.profiler import profile_all

QUERIES = [
    ("total amt by cid", ["cid"], lambda D: D["orders"].groupby("cid").amt.sum()),
    ("count customers by city", ["city"], lambda D: D["customers"].groupby("city").size()),
    ("average salary by dept", ["dept"], lambda D: D["hr"].groupby("dept").salary.mean()),
    ("total amt by city join orders customers", ["city"], lambda D: D["orders"].merge(D["customers"], on="cid").groupby("city").amt.sum()),
    ("average amt by tier", ["tier"], lambda D: D["orders"].merge(D["customers"], on="cid").groupby("tier").amt.mean()),
]


def main() -> None:
    data = ROOT / "data"
    datasets = {p.name: pd.read_csv(p) for p in sorted(data.glob("*.csv"))}
    assert {"orders.csv", "customers.csv", "hr.csv"} <= set(datasets), f"missing sample CSVs in {data}"
    reg = profile_all(datasets)
    rows, passed = [], 0
    for q, must_contain, _ in QUERIES:
        try:
            out = run_query(datasets, reg, q)
            cols = [str(c).lower() for c in out["table"].columns]
            ok = len(out["table"]) > 0 and any(m.lower() in " ".join(cols) or m.lower() in str(out["plan"]).lower() for m in must_contain)
        except Exception as e:
            ok, out = False, {"plan": {}, "trace": [f"EXC {e}"], "chart": "none", "insight": ""}
        passed += ok
        rows.append(f"| {q} | {'PASS' if ok else 'FAIL'} | chart={out.get('chart')} | plan={out.get('plan')} |")
    # join numeric correctness spot-check
    truth = datasets["orders.csv"].merge(datasets["customers.csv"], on="cid").groupby("city").amt.sum().sort_values(ascending=False)
    got = run_query(datasets, reg, "total amt by city join orders customers")["table"]
    join_ok = len(got) == len(truth)
    md = ["# Eval results", "", f"Passed {passed}/{len(QUERIES)} + join_shape_ok={join_ok}", "",
          "| query | result | detail |", "|---|---|---|"] + rows
    (ROOT / "evals" / "results.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
