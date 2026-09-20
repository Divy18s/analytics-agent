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
