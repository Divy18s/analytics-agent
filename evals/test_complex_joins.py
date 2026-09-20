"""Test runner for complex multi-table joins across 5 CSVs.

Loads complex_data/*.csv, executes 5 complex test queries,
stores query retrieval code & outputs, and compares agent results
against Pandas ground truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from graph import run_query
from tools.profiler import profile_all

DATA_DIR = ROOT / "complex_data"

TEST_CASES = [
    {
        "id": 1,
        "question": "total shipping cost by city joining orders and customers",
        "group_col": "city",
        "metric_col": "shipping_cost",
        "ground_truth_fn": lambda D: (
            D["orders.csv"]
            .merge(D["customers.csv"], on="customer_id", how="left")
            .groupby("city")["shipping_cost"]
            .sum()
            .reset_index()
            .rename(columns={"shipping_cost": "ground_truth_val"})
            .sort_values("ground_truth_val", ascending=False)
        ),
    },
    {
        "id": 2,
        "question": "average unit price by category name joining products and categories",
        "group_col": "category_name",
        "metric_col": "unit_price",
        "ground_truth_fn": lambda D: (
            D["products.csv"]
            .merge(D["categories.csv"], on="category_id", how="left")
            .groupby("category_name")["unit_price"]
            .mean()
            .reset_index()
            .rename(columns={"unit_price": "ground_truth_val"})
            .sort_values("ground_truth_val", ascending=False)
        ),
    },
    {
        "id": 3,
        "question": "total quantity by product name joining order items and products",
        "group_col": "product_name",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["products.csv"], on="product_id", how="left")
            .groupby("product_name")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "ground_truth_val"})
            .sort_values("ground_truth_val", ascending=False)
        ),
    },
    {
        "id": 4,
        "question": "total quantity by status joining order items and orders",
        "group_col": "status",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["orders.csv"], on="order_id", how="left")
            .groupby("status")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "ground_truth_val"})
            .sort_values("ground_truth_val", ascending=False)
        ),
    },
    {
        "id": 5,
        "question": "total shipping cost by membership joining orders and customers",
        "group_col": "membership",
        "metric_col": "shipping_cost",
        "ground_truth_fn": lambda D: (
            D["orders.csv"]
            .merge(D["customers.csv"], on="customer_id", how="left")
            .groupby("membership")["shipping_cost"]
            .sum()
            .reset_index()
            .rename(columns={"shipping_cost": "ground_truth_val"})
            .sort_values("ground_truth_val", ascending=False)
        ),
    },
]


def compare_tables(got: pd.DataFrame, truth: pd.DataFrame, group_col: str) -> tuple[bool, str]:
    if got.empty:
        return False, "Agent returned empty DataFrame"
    
    # Identify the metric column in agent table (usually 2nd column or 'val')
    agent_cols = list(got.columns)
    matched_group = next((c for c in agent_cols if c.lower() == group_col.lower()), None)
    if not matched_group:
        return False, f"Missing expected group column '{group_col}' in columns: {agent_cols}"
    
    val_cols = [c for c in agent_cols if c != matched_group]
    if not val_cols:
        return False, f"No value/metric column found in table: {agent_cols}"
    
    agent_val_col = val_cols[0]

    # Convert to comparable dictionaries keyed by group name
    got_dict = dict(zip(got[matched_group].astype(str).str.strip(), got[agent_val_col]))
    truth_dict = dict(zip(truth[group_col].astype(str).str.strip(), truth["ground_truth_val"]))

    # Check key overlap
    mismatches = []
    for k, expected_v in truth_dict.items():
        if k not in got_dict:
            mismatches.append(f"Missing key '{k}'")
        else:
            actual_v = got_dict[k]
            # allow small float delta
            if abs(float(actual_v) - float(expected_v)) > 0.05:
                mismatches.append(f"Key '{k}': expected {expected_v}, got {actual_v}")

    if mismatches:
        return False, "; ".join(mismatches[:3])
    return True, "Exact numerical match"


def main():
    print(f"Loading 5 CSV files from {DATA_DIR}...")
    datasets = {f.name: pd.read_csv(f) for f in sorted(DATA_DIR.glob("*.csv"))}
    print(f"Datasets loaded: {list(datasets.keys())}\n")

    reg = profile_all(datasets)
    print("Detected Join Candidates:")
    for k, v in reg["join_candidates"].items():
        print(f"  {k} -> {v}")
    print("=" * 70)

    results = []
    passed_count = 0

    for tc in TEST_CASES:
        qid = tc["id"]
        q = tc["question"]
        g_col = tc["group_col"]
        truth_df = tc["ground_truth_fn"](datasets)
        
        print(f"\n[Test Query {qid}]: '{q}'")
        out = run_query(datasets, reg, q)
        
        got_df = out["table"]
        code_used = out["code"]
        plan_used = out["plan"]
        is_match, reason = compare_tables(got_df, truth_df, g_col)

        status = "PASSED" if is_match else "FAILED"
        if is_match:
            passed_count += 1

        print(f"  Status: {status} ({reason})")
        print(f"  Plan: {plan_used}")
        print(f"  Retrieval Code:\n    {code_used}")
        print("  Agent Result Head:")
        print(got_df.head(3).to_string(index=False))
        print("  Ground Truth Head:")
        print(truth_df.head(3).to_string(index=False))

        results.append({
            "id": qid,
            "question": q,
            "status": status,
            "reason": reason,
            "plan": plan_used,
            "retrieval_code": code_used,
            "agent_table": got_df.to_dict(orient="records"),
            "ground_truth_table": truth_df.to_dict(orient="records"),
            "insight": out["insight"],
            "chart": out["chart"],
            "trace": out["trace"]
        })

    eval_json_path = ROOT / "evals" / "complex_test_results.json"
    eval_json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Generate Markdown Comparison Report
    md_lines = [
        "# Complex Multi-CSV Join Evaluation & Retrieval Audit",
        "",
        f"**Summary:** {passed_count}/{len(TEST_CASES)} queries passed ground truth verification.",
        "",
        "## Test Results Summary",
        "",
        "| ID | Query | Result | Retrieval Code Summary | Details |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        code_single_line = r["retrieval_code"].replace("\n", " ").replace("|", "\\|")[:80] + "..."
        md_lines.append(
            f"| {r['id']} | {r['question']} | **{r['status']}** | `{code_single_line}` | {r['reason']} |"
        )

    md_lines.append("\n## Detailed Comparisons\n")
    for r in results:
        md_lines.extend([
            f"### Query {r['id']}: {r['question']}",
            f"- **Status:** {r['status']} ({r['reason']})",
            f"- **Plan:** `{json.dumps(r['plan'])}`",
            "- **Retrieval Code Used:**",
            "```python",
            r["retrieval_code"],
            "```",
            f"- **Insight:** {r['insight']}",
            "",
            "**Agent Retrieved Output:**",
            pd.DataFrame(r["agent_table"]).to_markdown(index=False) if r["agent_table"] else "*(Empty)*",
            "",
            "**Expected Ground Truth:**",
            pd.DataFrame(r["ground_truth_table"]).to_markdown(index=False),
            "",
            "---",
            ""
        ])

    eval_md_path = ROOT / "evals" / "complex_test_results.md"
    eval_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nSaved detailed comparison report to {eval_md_path}")


if __name__ == "__main__":
    main()
