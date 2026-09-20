"""Baseline evaluation suite: single-file aggregations and 2-table joins."""
import pandas as pd

SUITE_NAME = "01_Baseline"
DESCRIPTION = "Core single-file operations and 2-table joins with mathematical validation"

TESTS = [
    {
        "id": "base-1",
        "question": "total amt by cid",
        "group_col": "cid",
        "metric_col": "amt",
        "ground_truth_fn": lambda D: (
            D["orders.csv"].groupby("cid")["amt"].sum().reset_index().rename(columns={"amt": "truth"})
        ),
    },
    {
        "id": "base-2",
        "question": "count customers by city",
        "group_col": "city",
        "metric_col": "cid",
        "ground_truth_fn": lambda D: (
            D["customers.csv"].groupby("city")["cid"].count().reset_index().rename(columns={"cid": "truth"})
        ),
    },
    {
        "id": "base-3",
        "question": "average salary by dept",
        "group_col": "dept",
        "metric_col": "salary",
        "ground_truth_fn": lambda D: (
            D["hr.csv"].groupby("dept")["salary"].mean().reset_index().rename(columns={"salary": "truth"})
        ),
    },
    {
        "id": "base-4",
        "question": "total amt by city joining orders and customers",
        "group_col": "city",
        "metric_col": "amt",
        "ground_truth_fn": lambda D: (
            D["orders.csv"]
            .merge(D["customers.csv"], on="cid", how="left")
            .groupby("city")["amt"]
            .sum()
            .reset_index()
            .rename(columns={"amt": "truth"})
        ),
    },
    {
        "id": "base-5",
        "question": "average amt by tier joining orders and customers",
        "group_col": "tier",
        "metric_col": "amt",
        "ground_truth_fn": lambda D: (
            D["orders.csv"]
            .merge(D["customers.csv"], on="cid", how="left")
            .groupby("tier")["amt"]
            .mean()
            .reset_index()
            .rename(columns={"amt": "truth"})
        ),
    },
]
