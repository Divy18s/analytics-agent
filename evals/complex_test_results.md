# Complex Multi-CSV Join Evaluation & Retrieval Audit

**Summary:** 5/5 queries passed ground truth verification.

## Test Results Summary

| ID | Query | Result | Retrieval Code Summary | Details |
|---|---|---|---|---|
| 1 | total shipping cost by city joining orders and customers | **PASSED** | `m = D['orders'].merge(D['customers'], on='customer_id', how='left') result = m.g...` | Exact numerical match |
| 2 | average unit price by category name joining products and categories | **PASSED** | `m = D['products'].merge(D['categories'], on='category_id', how='left') result = ...` | Exact numerical match |
| 3 | total quantity by product name joining order items and products | **PASSED** | `m = D['order_items'].merge(D['products'], on='product_id', how='left') result = ...` | Exact numerical match |
| 4 | total quantity by status joining order items and orders | **PASSED** | `m = D['order_items'].merge(D['orders'], on='order_id', how='left') result = m.gr...` | Exact numerical match |
| 5 | total shipping cost by membership joining orders and customers | **PASSED** | `m = D['orders'].merge(D['customers'], on='customer_id', how='left'); result = m....` | Exact numerical match |

## Detailed Comparisons

### Query 1: total shipping cost by city joining orders and customers
- **Status:** PASSED (Exact numerical match)
- **Plan:** `{"datasets": ["orders.csv", "customers.csv"], "join": {"left": "orders", "right": "customers", "on": "customer_id", "how": "left"}, "op": "groupby", "group_col": "city", "metric_col": "shipping_cost", "agg": "sum", "limit": 1000}`
- **Retrieval Code Used:**
```python
m = D['orders'].merge(D['customers'], on='customer_id', how='left')
result = m.groupby('city').agg(val=('shipping_cost','sum')).reset_index().head(1000)
```
- **Insight:** Bangalore 110.0, Delhi 90.0, Hyderabad 130.0, Mumbai 60.0  
vs‑average (97.5): Bangalore +12.5, Delhi ‑7.5, Hyderabad +32.5, Mumbai ‑37.5

**Agent Retrieved Output:**
| city      |   val |
|:----------|------:|
| Bangalore |   110 |
| Delhi     |    90 |
| Hyderabad |   130 |
| Mumbai    |    60 |

**Expected Ground Truth:**
| city      |   ground_truth_val |
|:----------|-------------------:|
| Hyderabad |                130 |
| Bangalore |                110 |
| Delhi     |                 90 |
| Mumbai    |                 60 |

---

### Query 2: average unit price by category name joining products and categories
- **Status:** PASSED (Exact numerical match)
- **Plan:** `{"datasets": ["products.csv", "categories.csv"], "join": {"left": "products", "right": "categories", "on": "category_id", "how": "left"}, "op": "groupby", "group_col": "category_name", "metric_col": "unit_price", "agg": "mean", "limit": 0}`
- **Retrieval Code Used:**
```python
m = D['products'].merge(D['categories'], on='category_id', how='left')
result = m.groupby('category_name').agg(val=('unit_price', 'mean')).reset_index().head()
```
- **Insight:** Furniture, 325.0  
vs-average, 109.4

**Agent Retrieved Output:**
| category_name   |   val |
|:----------------|------:|
| Apparel         |  45   |
| Electronics     |  50   |
| Furniture       | 325   |
| Stationery      |  17.5 |

**Expected Ground Truth:**
| category_name   |   ground_truth_val |
|:----------------|-------------------:|
| Furniture       |              325   |
| Electronics     |               50   |
| Apparel         |               45   |
| Stationery      |               17.5 |

---

### Query 3: total quantity by product name joining order items and products
- **Status:** PASSED (Exact numerical match)
- **Plan:** `{"datasets": ["order_items.csv", "products.csv"], "join": {"left": "order_items", "right": "products", "on": "product_id", "how": "left"}, "op": "groupby", "group_col": "product_name", "metric_col": "quantity", "agg": "sum", "limit": 0}`
- **Retrieval Code Used:**
```python
m = D['order_items'].merge(D['products'], on='product_id', how='left')
result = m.groupby('product_name').agg(val=('quantity', 'sum')).reset_index()
```
- **Insight:** Cotton T-Shirt: 2, Denim Jeans: 2, Ergonomic Chair: 2, Gel Pen Set: 7, Mechanical Keyboard: 2, Notebook Pack: 5, Standing Desk: 2, Wireless Mouse: 7  
vs‑average (3.4): Cotton T-Shirt (below), Denim Jeans (below), Ergonomic Chair (below), Gel Pen Set (above), Mechanical Keyboard (below), Notebook Pack (above), Standing Desk (below), Wireless Mouse (above)

**Agent Retrieved Output:**
| product_name        |   val |
|:--------------------|------:|
| Cotton T-Shirt      |     2 |
| Denim Jeans         |     2 |
| Ergonomic Chair     |     2 |
| Gel Pen Set         |     7 |
| Mechanical Keyboard |     2 |
| Notebook Pack       |     5 |
| Standing Desk       |     2 |
| Wireless Mouse      |     7 |

**Expected Ground Truth:**
| product_name        |   ground_truth_val |
|:--------------------|-------------------:|
| Gel Pen Set         |                  7 |
| Wireless Mouse      |                  7 |
| Notebook Pack       |                  5 |
| Cotton T-Shirt      |                  2 |
| Ergonomic Chair     |                  2 |
| Denim Jeans         |                  2 |
| Mechanical Keyboard |                  2 |
| Standing Desk       |                  2 |

---

### Query 4: total quantity by status joining order items and orders
- **Status:** PASSED (Exact numerical match)
- **Plan:** `{"datasets": ["order_items.csv", "orders.csv"], "join": {"left": "order_items", "right": "orders", "on": "order_id", "how": "left"}, "op": "groupby", "group_col": "status", "metric_col": "quantity", "agg": "sum", "limit": 0}`
- **Retrieval Code Used:**
```python
m = D['order_items'].merge(D['orders'], on='order_id', how='left')
result = m.groupby('status').agg(val=('quantity','sum')).reset_index().head(20)
```
- **Insight:** Delivered,18
vs-average,18,7.25

**Agent Retrieved Output:**
| status    |   val |
|:----------|------:|
| Cancelled |     2 |
| Delivered |    18 |
| Pending   |     3 |
| Shipped   |     6 |

**Expected Ground Truth:**
| status    |   ground_truth_val |
|:----------|-------------------:|
| Delivered |                 18 |
| Shipped   |                  6 |
| Pending   |                  3 |
| Cancelled |                  2 |

---

### Query 5: total shipping cost by membership joining orders and customers
- **Status:** PASSED (Exact numerical match)
- **Plan:** `{"datasets": ["orders.csv", "customers.csv"], "join": {"left": "orders", "right": "customers", "on": "customer_id", "how": "left"}, "op": "groupby", "group_col": "membership", "metric_col": "shipping_cost", "agg": "sum", "limit": 0}`
- **Retrieval Code Used:**
```python
m = D['orders'].merge(D['customers'], on='customer_id', how='left'); result = m.groupby('membership').agg(val=('shipping_cost','sum')).reset_index().sort_values('val', ascending=False).head(20)
```
- **Insight:** Gold: 160.0, Platinum: 155.0, Silver: 50.0, Bronze: 25.0  
Average: 97.5

**Agent Retrieved Output:**
| membership   |   val |
|:-------------|------:|
| Gold         |   160 |
| Platinum     |   155 |
| Silver       |    50 |
| Bronze       |    25 |

**Expected Ground Truth:**
| membership   |   ground_truth_val |
|:-------------|-------------------:|
| Gold         |                160 |
| Platinum     |                155 |
| Silver       |                 50 |
| Bronze       |                 25 |

---
