"""Scaled 15,000-row evaluation suite: testing multi-table joins at production scale."""
import pandas as pd

SUITE_NAME = "05_Scaled_15k"
DESCRIPTION = "Production-scale dataset with 15,000 line items, 6,000 orders, and multi-table joins"

TESTS = [
    {
        "id": "scale-1",
        "question": "total shipping cost by city joining orders and customers",
        "group_col": "city",
        "metric_col": "shipping_cost",
        "ground_truth_fn": lambda D: (
            D["orders.csv"]
            .merge(D["customers.csv"], on="customer_id", how="left")
            .groupby("city")["shipping_cost"]
            .sum()
            .reset_index()
            .rename(columns={"shipping_cost": "truth"})
        ),
    },
    {
        "id": "scale-2",
        "question": "total quantity by product name joining order items and products",
        "group_col": "product_name",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["products.csv"], on="product_id", how="left")
            .groupby("product_name")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "truth"})
        ),
    },
    {
        "id": "scale-3",
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
]
