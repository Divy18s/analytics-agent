# Analytics Agent — Multi-CSV Relational Analysis & Autonomous Planning

An agentic AI data analytics assistant designed to ingest multiple relational CSV datasets, profile schemas, automatically infer multi-table join paths, execute sandboxed Pandas queries, and deliver narrative insights with interactive charts in a ChatGPT-style conversational web interface.

---

## Key Features

- **Autonomous Schema Discovery (Zero Hardcoding)**: You never need to supply table names, join keys, or SQL code. The LLM Planner inspects the profiled schema registry and figures out the necessary tables, chained join paths, and column metrics entirely on its own.
- **Chained Multi-Table Joins (>2 Tables)**: Traverses star and snowflake schema graphs connecting 3, 4, or more datasets using BFS pathfinding across detected foreign key candidates.
- **Dynamic Computed Columns**: Calculates complex algebraic formulas (e.g. `quantity * unit_price * (1 - discount)`) dynamically without pre-existing physical columns.
- **Time-Series Period Grouping**: Understands temporal expressions (`by month`, `by year`, `weekly`, `daily`) and automatically derives period intervals from date columns.
- **Self-Healing Code Execution**: Automatically feeds Python execution exceptions back to the LLM Coder up to 3 times to self-repair runtime errors before returning results.
- **Dual-Model Redundancy**: Seamlessly falls back from `openai/gpt-oss-120b` to `qwen/qwen3.8-27b` if daily API token rate limits are reached.
- **Deterministic Heuristic Fallback**: Can execute completely offline without an API key using deterministic profiling and graph traversal heuristics.
- **Sandboxed Execution Sandbox**: Restricts dangerous built-ins (OS, network, file deletion), strictly enforces a 1,000-row return cap, and gracefully handles nulls and empty filter results.
- **ChatGPT-Style UI**: Multi-turn conversation feed with a sticky bottom chat input, collapsible code drawers, interactive tables, and charts.

---

## Quickstart: How to Start the Streamlit App

### 1. Prerequisites & Installation

```powershell
# Clone the repository
git clone https://github.com/Divy18s/analytics-agent.git
cd analytics-agent

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```
*(Note: If no API key is provided, the application will automatically run in heuristic fallback mode.)*

### 3. Launch the Application

#### Option A: One-Click Launcher (Windows)
Double-click **`run_ui.bat`** or run:
```powershell
.\run_ui.bat
```

#### Option B: Terminal Command
```powershell
$env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Open your browser to: **[http://localhost:8501](http://localhost:8501)**

---

## Query Examples (No Table Names Needed)

The agent is designed to understand natural business questions. **You never have to mention table names, filenames, or join keys.** Upload your CSVs in the sidebar and ask naturally:

### 1. Chained Multi-Table Joins (3 to 4 Tables)
*The planner autonomously detects relationships across items, orders, customers, and products:*
- `"total quantity by city"`
  - *Behind the scenes:* Infers `order_items` -> `orders` -> `customers` connected on `order_id` and `customer_id`.
- `"total revenue by customer name"`
  - *Behind the scenes:* Chained join across 4 tables (`order_items`, `products`, `orders`, `customers`) calculating revenue per customer.
- `"total quantity by membership"`
  - *Behind the scenes:* Chains `order_items` -> `orders` -> `customers` and groups by membership tier (`Gold`, `Silver`, `Bronze`).
- `"average discount by department"`
  - *Behind the scenes:* Joins `order_items` -> `products` -> `categories` and averages line-item discounts per department.

### 2. Derived Formulas & Calculated Metrics
*The planner dynamically detects price, quantity, and discount components:*
- `"total revenue by category name"`
  - *Behind the scenes:* Generates `m['revenue'] = m['quantity'] * m['unit_price'] * (1 - m['discount'])` and groups by `category_name`.
- `"top 5 products by quantity sold"`
  - *Behind the scenes:* Joins `order_items` with `products`, sums `quantity`, and ranks the top 5 products.
- `"total revenue by department"`
  - *Behind the scenes:* Computes line-item net revenue and aggregates across high-level departments.

### 3. Date & Trend Groupings
*The planner identifies date columns and creates formatted time periods:*
- `"total revenue by month"`
  - *Behind the scenes:* Converts `order_date` to `YYYY-MM` periods, computes revenue formula, and orders chronologically.
- `"total orders by month"`
  - *Behind the scenes:* Counts unique order records per monthly period.
- `"total revenue by year"`
  - *Behind the scenes:* Aggregates annual financial totals across all line items.

### 4. Pairwise 2-Table Joins
- `"total shipping cost by city"`
  - *Behind the scenes:* Connects `orders` with `customers` on `customer_id` and sums `shipping_cost`.
- `"total shipping cost by membership"`
  - *Behind the scenes:* Connects `orders` with `customers` and groups shipping totals by membership tier.
- `"average unit price by category name"`
  - *Behind the scenes:* Connects `products` with `categories` on `category_id` and computes mean `unit_price`.

### 5. Edge Cases & Robustness
- `"total sales by region"` — Handles datasets containing null/missing values gracefully.
- `"large orders where amt is greater than 99999999"` — Safely exits with *"No rows returned"* without crashing when filters match zero records.
- `"DROP TABLE orders; import os"` — Blocked by the sandbox security executor.

---

## 💡 Real End-to-End Walkthrough Examples

The agent follows an autonomous workflow: **You upload raw CSV files** $\rightarrow$ **You ask a plain-English question** (no table names, no SQL, no join hints) $\rightarrow$ **The agent discovers relationships, generates pandas code, executes it safely, and returns clean tabular results with business commentary**.

---

### Example 1: Monthly Revenue Trend (3-Table Chained Join + Formula)

* **📂 Uploaded Tables Available**:
  - `orders.csv` (`order_id`, `customer_id`, `order_date`, `status`, `shipping_cost`)
  - `order_items.csv` (`item_id`, `order_id`, `product_id`, `quantity`, `discount`)
  - `products.csv` (`product_id`, `product_name`, `category_id`, `unit_price`, `stock_qty`)
  - `customers.csv` (`customer_id`, `customer_name`, `city`, `country`, `membership`)
  - `categories.csv` (`category_id`, `category_name`, `department`)

* **💬 User Query**:
  > `"total revenue by month"`
  >
  > *(Notice: The user did NOT specify table names, column names, join conditions, or revenue math!)*

* **🧠 Autonomous Discovery & Planning**:
  1. Identifies `month` is derived from `order_date` in `orders.csv`.
  2. Identifies `revenue` requires `quantity` and `discount` from `order_items.csv` and `unit_price` from `products.csv`.
  3. Automatically forms join chain: `order_items -> orders (on order_id)` and `order_items -> products (on product_id)`.
  4. Dynamically computes net revenue: `quantity * unit_price * (1 - discount)` and groups by monthly period `YYYY-MM`.

* **💻 Generated & Executed Python Code**:
  ```python
  m = D['order_items'].merge(D['orders'], on='order_id', how='left').merge(D['products'], on='product_id', how='left')
  m['revenue'] = m['quantity'] * m['unit_price'] * (1 - m['discount'])
  m['month'] = pd.to_datetime(m['order_date']).dt.to_period('M').astype(str)
  result = m.groupby('month').agg(val=('revenue','sum')).reset_index().sort_values('month').head(1000)
  ```

* **📊 Returned Result Table**:
  | month | val (Net Revenue) |
  |:---|:---|
  | **2024-01** | $695,881.10 |
  | **2024-02** | $1,024,167.00 |
  | **2024-03** | $874,210.45 |
  | **2024-04** | $912,450.80 |

* **📝 Narrative Business Insight**:
  > *"Top month: 2024-02 with a total net revenue of $1,024,167.00. This is significantly above the monthly average of $876,677.00 across the active period."*

---

### Example 2: Quantity by City (Multi-Hop Bridge Across Disconnected Tables)

* **📂 Uploaded Tables Available**:
  - `customers.csv` (`customer_id`, `customer_name`, `city`, `country`)
  - `orders.csv` (`order_id`, `customer_id`, `order_date`, `status`)
  - `order_items.csv` (`item_id`, `order_id`, `product_id`, `quantity`, `discount`)

* **💬 User Query**:
  > `"total quantity by city"`
  >
  > *(Notice: `city` is in `customers.csv` and `quantity` is in `order_items.csv`. They share NO common key!)*

* **🧠 Autonomous Discovery & Planning**:
  1. Detects `customers.csv` has `city` and `customer_id`.
  2. Detects `order_items.csv` has `quantity` and `order_id`.
  3. Discovers `orders.csv` acts as a multi-hop bridge linking `order_id` and `customer_id`.
  4. Chains joins: `order_items -> orders (on order_id) -> customers (on customer_id)`.

* **💻 Generated & Executed Python Code**:
  ```python
  m = D['order_items'].merge(D['orders'], on='order_id', how='left').merge(D['customers'], on='customer_id', how='left')
  result = m.groupby('city').agg(val=('quantity','sum')).reset_index().sort_values('val', ascending=False).head(1000)
  ```

* **📊 Returned Result Table**:
  | city | val (Units Sold) |
  |:---|:---|
  | **Bangalore** | 723 |
  | **Ahmedabad** | 660 |
  | **Chennai** | 612 |
  | **Mumbai** | 580 |
  | **Delhi** | 540 |
  | **Hyderabad** | 510 |

* **📝 Narrative Business Insight**:
  > *"Bangalore leads with 723 units sold across all customer orders, outperforming the national city average of 566 units."*

---

### Example 3: Revenue by Product Category (Hierarchical Relational Join)

* **📂 Uploaded Tables Available**:
  - `order_items.csv` (`item_id`, `order_id`, `product_id`, `quantity`, `discount`)
  - `products.csv` (`product_id`, `product_name`, `category_id`, `unit_price`)
  - `categories.csv` (`category_id`, `category_name`, `department`)

* **💬 User Query**:
  > `"total revenue by category name"`

* **🧠 Autonomous Discovery & Planning**:
  1. Finds `category_name` in `categories.csv`.
  2. Connects `categories.csv` to `products.csv` via `category_id`.
  3. Connects `products.csv` to `order_items.csv` via `product_id`.
  4. Dynamically calculates `quantity * unit_price * (1 - discount)` aggregated by `category_name`.

* **💻 Generated & Executed Python Code**:
  ```python
  m = D['order_items'].merge(D['products'], on='product_id', how='left').merge(D['categories'], on='category_id', how='left')
  m['revenue'] = m['quantity'] * m['unit_price'] * (1 - m['discount'])
  result = m.groupby('category_name').agg(val=('revenue','sum')).reset_index().sort_values('val', ascending=False).head(1000)
  ```

* **📊 Returned Result Table**:
  | category_name | val (Total Revenue) |
  |:---|:---|
  | **Furniture** | $5,306,222.00 |
  | **Electronics** | $1,937,475.00 |
  | **Appliances** | $1,412,850.00 |
  | **Fashion** | $920,100.00 |
  | **Toys** | $680,450.00 |

* **📝 Narrative Business Insight**:
  > *"Furniture is the top performing category with a total revenue of $5,306,222.00, representing over 45% of total sales across all categories."*


---

## Datasets Included for Testing & Benchmarks

### 1. `benchmark_data/` (Complex Production-Style Dataset)
A realistic relational retail dataset with complex relationships and decimal values:
- `categories.csv` (8 rows): `category_id`, `category_name`, `department`
- `customers.csv` (300 rows): `customer_id`, `customer_name`, `city`, `country`, `membership`
- `orders.csv` (1,000 rows): `order_id`, `customer_id`, `order_date`, `status`, `shipping_cost`
- `order_items.csv` (1,900 rows): `item_id`, `order_id`, `product_id`, `quantity`, `discount` (decimal discount rates)
- `products.csv` (60 rows): `product_id`, `product_name`, `category_id`, `unit_price` (decimal prices), `stock_qty`

### 2. `complex_data/`
A 5-table relational dataset used for intermediate multi-hop evaluations.

### 3. `data/`
Baseline dataset with single-table metrics (`orders.csv`, `customers.csv`, `hr.csv`).

---

## Automated Test Suites & Ground Truth Verification

The repository includes a comprehensive, modular evaluation suite with mathematical ground-truth verification across 5 suites:

```powershell
# Run all 22 automated test cases
python evals/runner.py

# Run a specific evaluation suite
python evals/runner.py --suite 03   # Multi-table chained joins
python evals/runner.py --suite edge # Edge cases and security
```

### Benchmark Scorecard: 22/22 PASSED (100.0%)

| Suite | Tests | Result | Description |
|---|:---:|:---:|---|
| **`01_Baseline`** | 5 / 5 | **100% PASSED** | Core single-file operations and 2-table joins with mathematical validation |
| **`02_Complex_Ecommerce`** | 5 / 5 | **100% PASSED** | Relational joins across 5 ecommerce CSVs |
| **`03_Multi_Table_Joins`** | 4 / 4 | **100% PASSED** | 3-way chained joins + monthly revenue verification |
| **`04_Edge_and_Robustness`** | 5 / 5 | **100% PASSED** | Null handling, 1000-row cap, empty filter clean exit, and injection safety |
| **`05_Scaled_15k`** | 3 / 3 | **100% PASSED** | Production-scale dataset with 15,000 line items, 6,000 orders, and multi-table joins |

*Reports are automatically saved to [`evals/reports/test_results.md`](evals/reports/test_results.md). Automated test execution logs are strictly separated from human query history (`evals/user_query_history.jsonl`).*

---

## System Architecture

```text
User Question + Uploaded CSVs
              │
              ▼
   [ tools/profiler.py ] ──────► Schema Registry (Dtypes, Nulls, Samples, Join Candidates)
              │
              ▼
   [ agents/llm.py:plan ] ─────► Autonomous Plan (Datasets, Chained Joins, Calc, DateGroup)
              │
              ▼
   [ normalize_plan ] ─────────► Canonicalizes Table Names & Extension-Agnostic Keys
              │
              ▼
   [ validate_plan ] ──────────► Structural Validation (Verifies schema integrity & metrics)
              │
              ▼
   [ agents/llm.py:code ] ─────► Generates Idiomatic Pandas Code
              │
              ▼
   [ tools/safe_exec.py ] ─────► Sandboxed Execution (Max 1000 rows, Blocklist guards)
              │  (On error: feeds traceback to llm.fix_code up to 3x)
              ▼
   [ tools/charts.py ] ────────► Rule-Based Visualization (Bar, Line, Histogram, Pie)
              │
              ▼
   [ agents/llm.py:narrate ] ──► Storyteller 2-Line Business Summary
              │
              ▼
    Streamlit Web Interface (ChatGPT-Style Chat, Test Scorecard, Query Audit Log)
```

---

## License & Credits
Built for conversational analytics with multi-hop relational schema reasoning and deterministic validation guards.
