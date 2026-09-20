"""Complex ecommerce evaluation suite: 5-table relational pairwise joins."""
import pandas as pd

SUITE_NAME = "02_Complex_Ecommerce"
DESCRIPTION = "2-table relational joins across 5 ecommerce CSVs"

TESTS = [
    {
        "id": "cmplx-1",
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
        "id": "cmplx-2",
        "question": "average unit price by category name joining products and categories",
        "group_col": "category_name",
        "metric_col": "unit_price",
        "ground_truth_fn": lambda D: (
            D["products.csv"]
            .merge(D["categories.csv"], on="category_id", how="left")
            .groupby("category_name")["unit_price"]
            .mean()
            .reset_index()
            .rename(columns={"unit_price": "truth"})
        ),
    },
    {
        "id": "cmplx-3",
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
        "id": "cmplx-4",
        "question": "total quantity by status joining order items and orders",
        "group_col": "status",
        "metric_col": "quantity",
        "ground_truth_fn": lambda D: (
            D["order_items.csv"]
            .merge(D["orders.csv"], on="order_id", how="left")
            .groupby("status")["quantity"]
            .sum()
            .reset_index()
            .rename(columns={"quantity": "truth"})
        ),
    },
    {
        "id": "cmplx-5",
        "question": "total shipping cost by membership joining orders and customers",
        "group_col": "membership",
        "metric_col": "shipping_cost",
        "ground_truth_fn": lambda D: (
            D["orders.csv"]
            .merge(D["customers.csv"], on="customer_id", how="left")
            .groupby("membership")["shipping_cost"]
            .sum()
            .reset_index()
            .rename(columns={"shipping_cost": "truth"})
        ),
    },
]
