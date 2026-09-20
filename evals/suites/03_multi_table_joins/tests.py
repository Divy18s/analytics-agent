"""Multi-table evaluation suite: 3-way chained joins (>2 tables)."""
import pandas as pd

SUITE_NAME = "03_Multi_Table_Joins"
DESCRIPTION = "3-way chained relational joins connecting 3+ datasets"

TESTS = [
    {
        "id": "multi-1",
        "question": "total quantity by city joining order items orders customers",
        "group_col": "city",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["orders.csv"], on="order_id", how="left")
            .merge(D["customers.csv"], on="customer_id", how="left")
            .groupby("city")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "truth"})
        ),
    },
    {
        "id": "multi-2",
        "question": "total quantity by department joining order items products categories",
        "group_col": "department",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["products.csv"], on="product_id", how="left")
            .merge(D["categories.csv"], on="category_id", how="left")
            .groupby("department")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "truth"})
        ),
    },
    {
        "id": "multi-3",
        "question": "total quantity by membership joining order items orders customers",
        "group_col": "membership",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["orders.csv"], on="order_id", how="left")
            .merge(D["customers.csv"], on="customer_id", how="left")
            .groupby("membership")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "truth"})
        ),
    },
]
