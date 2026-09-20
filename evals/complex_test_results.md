# Consolidated Test Suite & Retrieval Audit

**Overall Score:** `21/21 PASSED` (100.0%)
**Generated:** 2026-09-20 12:59:52

## Summary by Test Suite

| Suite | Passed | Total | Rate | Status |
|---|---|---|---|---|
| **01_Baseline** | 5 | 5 | 100.0% | **PASSED** |
| **02_Complex_Ecommerce** | 5 | 5 | 100.0% | **PASSED** |
| **03_Multi_Table_Joins** | 3 | 3 | 100.0% | **PASSED** |
| **04_Edge_and_Robustness** | 5 | 5 | 100.0% | **PASSED** |
| **05_Scaled_15k** | 3 | 3 | 100.0% | **PASSED** |

## Detailed Test Cases & Ground Truth Comparison

### 01_Baseline
*Core single-file operations and 2-table joins with mathematical validation*

| ID | Query | Result | Retrieval Code | Details |
|---|---|---|---|---|
| `base-1` | total amt by cid | **PASSED** | `result = D['orders'].groupby('cid').agg(val=('amt','sum')).r...` | Exact numerical match |
| `base-2` | count customers by city | **PASSED** | `result = D['customers'].groupby('city').agg(val=('cid','coun...` | Exact numerical match |
| `base-3` | average salary by dept | **PASSED** | `result = D['hr.csv'].groupby('dept').agg(val=('salary','mean...` | Exact numerical match |
| `base-4` | total amt by city joining orders and customers | **PASSED** | `m = D['orders'].merge(D['customers'], on='cid', how='inner')...` | Exact numerical match |
| `base-5` | average amt by tier joining orders and customers | **PASSED** | `m = D['customers'].merge(D['orders'], on='cid', how='inner')...` | Exact numerical match |

### 02_Complex_Ecommerce
*2-table relational joins across 5 ecommerce CSVs*

| ID | Query | Result | Retrieval Code | Details |
|---|---|---|---|---|
| `cmplx-1` | total shipping cost by city joining orders and customers | **PASSED** | `m = D['orders'].merge(D['customers'], on='customer_id', how=...` | Exact numerical match |
| `cmplx-2` | average unit price by category name joining products and categories | **PASSED** | `m = D['products'].merge(D['categories'], on='category_id', h...` | Exact numerical match |
| `cmplx-3` | total quantity by product name joining order items and products | **PASSED** | `m = D['order_items'].merge(D['products'], on='product_id', h...` | Exact numerical match |
| `cmplx-4` | total quantity by status joining order items and orders | **PASSED** | `m = D['order_items'].merge(D['orders'], on='order_id', how='...` | Exact numerical match |
| `cmplx-5` | total shipping cost by membership joining orders and customers | **PASSED** | `m = D['orders'].merge(D['customers'], on='customer_id', how=...` | Exact numerical match |

### 03_Multi_Table_Joins
*3-way chained relational joins connecting 3+ datasets*

| ID | Query | Result | Retrieval Code | Details |
|---|---|---|---|---|
| `multi-1` | total quantity by city joining order items orders customers | **PASSED** | `m = D['order_items'].merge(D['orders'], on='order_id', how='...` | Exact numerical match |
| `multi-2` | total quantity by department joining order items products categories | **PASSED** | `m = D['order_items'].merge(D['products'], on='product_id', h...` | Exact numerical match |
| `multi-3` | total quantity by membership joining order items orders customers | **PASSED** | `m = D['order_items'].merge(D['orders'], on='order_id', how='...` | Exact numerical match |

### 04_Edge_and_Robustness
*Edge cases including null values, 1000-row cap, empty filters, and injection safety*

| ID | Query | Result | Retrieval Code | Details |
|---|---|---|---|---|
| `edge-1` | total sales by region | **PASSED** | `result = D['nulls_sales.csv'].groupby('region').agg(val=('sa...` | Gracefully aggregates table with null values without crashing |
| `edge-2` | show all large orders | **PASSED** | `m = D['large_orders.csv']; result = m.head(1200)...` | Enforces MAX_ROWS (1,000) safety cap on 1,200-row dataset |
| `edge-3` | large orders where amt is greater than 99999999 | **PASSED** | `m = D['large_orders.csv']; m = m[m['amt'] > 99999999]; resul...` | Empty filter terminates safely in <=3 attempts with 'No rows returned' |
| `edge-4` | total nonexistent_metric by nonexistent_dim | **PASSED** | `m = pd.DataFrame(); result = m.head(20)...` | Handles unrecognized columns gracefully without uncaught exceptions |
| `edge-5` | DROP TABLE orders; import os | **PASSED** | `m = pd.DataFrame(); result = m.head(20)...` | Sandboxed executor blocks malicious tokens (DROP TABLE, import os) |

### 05_Scaled_15k
*Production-scale dataset with 15,000 line items, 6,000 orders, and multi-table joins*

| ID | Query | Result | Retrieval Code | Details |
|---|---|---|---|---|
| `scale-1` | total shipping cost by city joining orders and customers | **PASSED** | `m = D['orders'].merge(D['customers'], on='customer_id', how=...` | Exact numerical match |
| `scale-2` | total quantity by product name joining order items and products | **PASSED** | `m = D['order_items'].merge(D['products'], on='product_id', h...` | Exact numerical match |
| `scale-3` | total quantity by city joining order items orders customers | **PASSED** | `m = D['order_items'].merge(D['orders'], on='order_id', how='...` | Exact numerical match |
