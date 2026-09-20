"""Unified Generic Test & Evaluation Runner.

Discovers and executes test suites in evals/suites/,
evaluates mathematical ground truths and edge cases,
and generates consolidated markdown & JSON reports.

Usage:
  python evals/runner.py                 # Runs all test suites
  python evals/runner.py --suite 01      # Runs suite matching '01'
  python evals/runner.py --suite multi   # Runs multi-table join suite
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from graph import run_query
from tools.profiler import profile_all

SUITES_DIR = ROOT / "evals" / "suites"
REPORTS_DIR = ROOT / "evals" / "reports"


def compare_tables(got: pd.DataFrame, truth: pd.DataFrame, group_col: str) -> tuple[bool, str]:
    if got.empty:
        return False, "Agent returned empty DataFrame"
    
    agent_cols = list(got.columns)
    matched_group = next((c for c in agent_cols if c.lower() == group_col.lower()), None)
    if not matched_group:
        return False, f"Missing group col '{group_col}' in columns: {agent_cols}"
    
    val_cols = [c for c in agent_cols if c != matched_group]
    if not val_cols:
        return False, f"No value/metric column found in table: {agent_cols}"
    
    agent_val_col = val_cols[0]
    truth_val_col = [c for c in truth.columns if c.lower() != group_col.lower()][0]

    got_dict = dict(zip(got[matched_group].astype(str).str.strip(), got[agent_val_col]))
    truth_dict = dict(zip(truth[group_col].astype(str).str.strip(), truth[truth_val_col]))

    mismatches = []
    for k, expected_v in truth_dict.items():
        if k not in got_dict:
            mismatches.append(f"Missing key '{k}'")
        else:
            try:
                actual_v = float(got_dict[k])
                exp_v = float(expected_v)
                if abs(actual_v - exp_v) > 0.05:
                    mismatches.append(f"Key '{k}': expected {exp_v}, got {actual_v}")
            except Exception:
                if str(got_dict[k]).strip() != str(expected_v).strip():
                    mismatches.append(f"Key '{k}': expected {expected_v}, got {got_dict[k]}")

    if mismatches:
        return False, "; ".join(mismatches[:3])
    return True, "Exact numerical match"


def load_suite_module(suite_dir: Path):
    tests_file = suite_dir / "tests.py"
    if not tests_file.exists():
        return None
    spec = importlib.util.spec_from_file_location(suite_dir.name, tests_file)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_suite(suite_dir: Path) -> dict:
    mod = load_suite_module(suite_dir)
    if not mod or not hasattr(mod, "TESTS"):
        return {"suite": suite_dir.name, "passed": 0, "total": 0, "tests": []}

    suite_name = getattr(mod, "SUITE_NAME", suite_dir.name)
    description = getattr(mod, "DESCRIPTION", "")
    data_dir = suite_dir / "data"
    
    datasets = {f.name: pd.read_csv(f) for f in sorted(data_dir.glob("*.csv"))}
    reg = profile_all(datasets)

    print(f"\n========================================================")
    print(f"Running Suite: {suite_name} ({len(datasets)} datasets)")
    print(f"Description: {description}")
    print(f"========================================================")

    test_results = []
    passed_count = 0

    for tc in mod.TESTS:
        tid = tc["id"]
        q = tc["question"]
        print(f"\n[{tid}] Question: '{q}'")
        
        start_time = time.time()
        try:
            # Use source="eval" so automated tests don't pollute human query history
            out = run_query(datasets, reg, q, source="eval")
        except Exception as e:
            out = {"plan": {}, "code": "", "table": pd.DataFrame(), "fig": None,
                   "chart": "none", "insight": "", "trace": [f"CRASH: {e}"], "error": str(e)}
        latency = round(time.time() - start_time, 2)

        got_df = out["table"]
        code_used = out["code"]
        plan_used = out["plan"]

        is_match = False
        reason = ""
        truth_records = []

        if "ground_truth_fn" in tc:
            g_col = tc["group_col"]
            try:
                truth_df = tc["ground_truth_fn"](datasets)
                is_match, reason = compare_tables(got_df, truth_df, g_col)
                truth_records = truth_df.head(5).to_dict(orient="records")
            except Exception as e:
                is_match = False
                reason = f"Ground truth evaluation error: {e}"
        elif "check_fn" in tc:
            try:
                is_match = bool(tc["check_fn"](out, datasets))
                reason = tc.get("expected_desc", "Passed custom verification check") if is_match else "Failed verification condition"
            except Exception as e:
                is_match = False
                reason = f"Check condition error: {e}"

        status = "PASSED" if is_match else "FAILED"
        if is_match:
            passed_count += 1

        print(f"  Result: {status} ({reason}) [{latency}s]")
        if code_used:
            print(f"  Code: {code_used[:100]}...")

        test_results.append({
            "id": tid,
            "suite": suite_name,
            "question": q,
            "status": status,
            "reason": reason,
            "plan": plan_used,
            "retrieval_code": code_used,
            "agent_table": got_df.head(5).to_dict(orient="records") if not got_df.empty else [],
            "ground_truth_table": truth_records,
            "latency": latency,
            "insight": out.get("insight", "")
        })

    return {
        "suite": suite_name,
        "description": description,
        "passed": passed_count,
        "total": len(mod.TESTS),
        "tests": test_results
    }


def generate_markdown_report(suite_reports: list[dict]) -> str:
    total_passed = sum(s["passed"] for s in suite_reports)
    total_tests = sum(s["total"] for s in suite_reports)
    pass_pct = round((total_passed / total_tests * 100), 1) if total_tests else 0

    lines = [
        "# Consolidated Test Suite & Retrieval Audit",
        "",
        f"**Overall Score:** `{total_passed}/{total_tests} PASSED` ({pass_pct}%)",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary by Test Suite",
        "",
        "| Suite | Passed | Total | Rate | Status |",
        "|---|---|---|---|---|",
    ]
    for s in suite_reports:
        rate = f"{round(s['passed']/s['total']*100, 1)}%" if s['total'] else "0%"
        status_icon = "PASSED" if s['passed'] == s['total'] else "PARTIAL"
        lines.append(f"| **{s['suite']}** | {s['passed']} | {s['total']} | {rate} | **{status_icon}** |")

    lines.append("\n## Detailed Test Cases & Ground Truth Comparison\n")

    for s in suite_reports:
        lines.extend([
            f"### {s['suite']}",
            f"*{s.get('description', '')}*",
            "",
            "| ID | Query | Result | Retrieval Code | Details |",
            "|---|---|---|---|---|",
        ])
        for t in s["tests"]:
            code_snippet = (t['retrieval_code'] or 'N/A').replace("\n", " ").replace("|", "\\|")[:60] + "..."
            lines.append(f"| `{t['id']}` | {t['question']} | **{t['status']}** | `{code_snippet}` | {t['reason']} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Unified Generic Test Runner")
    parser.add_argument("--suite", type=str, default="", help="Filter by suite directory name substring")
    args = parser.parse_args()

    suite_dirs = [p for p in sorted(SUITES_DIR.iterdir()) if p.is_dir()]
    if args.suite:
        suite_dirs = [p for p in suite_dirs if args.suite.lower() in p.name.lower()]

    if not suite_dirs:
        print(f"No test suites found in {SUITES_DIR} matching '{args.suite}'")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    all_reports = []

    for s_dir in suite_dirs:
        res = run_suite(s_dir)
        all_reports.append(res)

    # Save reports
    md_content = generate_markdown_report(all_reports)
    report_md_path = REPORTS_DIR / "test_results.md"
    report_json_path = REPORTS_DIR / "test_results.json"

    report_md_path.write_text(md_content, encoding="utf-8")
    report_json_path.write_text(json.dumps(all_reports, indent=2), encoding="utf-8")

    # Also sync to legacy paths for backwards compatibility with any existing bookmarks
    (ROOT / "evals" / "results.md").write_text(md_content, encoding="utf-8")
    (ROOT / "evals" / "complex_test_results.md").write_text(md_content, encoding="utf-8")

    print("\n" + "=" * 60)
    print("ALL TEST SUITES FINISHED")
    print(f"Report saved to: {report_md_path}")
    print("=" * 60)
    print(md_content)


if __name__ == "__main__":
    main()
