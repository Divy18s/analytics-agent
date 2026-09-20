# Analytics Agent v2 — multi-CSV + joins + evals (generic)

Upload 1..N CSVs → shared registry → ask across files (joins auto-detected) → table + chart + insight.

## Agents vs tools (interview-correct)
- Tools (deterministic): `tools/profiler.py` (registry + join candidates), `tools/safe_exec.py` (read-only sandbox, 1000-row cap), `tools/charts.py` (rule chart)
- Agents (LLM): Planner, Coder, Storyteller (`agents/`). Heuristic fallback = runs with no key.
- Supervisor `graph.py`: profile → plan (datasets + join?) → code ↔ execute (max 3) → validate → visualize.

## Run
```powershell
pip install -r requirements.txt
python evals/runner.py                 # Runs all 18 test suites (Baseline, Complex, Multi-Join, Edge)
python evals/runner.py --suite 03      # Runs only multi-table 3+ chained joins
streamlit run app.py                  # Launches ChatGPT-style analytics app
```
Set `GROQ_API_KEY` in `.env` (or `$env:GROQ_API_KEY`) for LLM planning/coding.

## What it does
- Single-file: groupby/topn/filter/describe on any CSV, auto charts.
- Multi-file & Multi-hop: detects shared keys (`join_candidates`), plans chained `merge()` joins across 2..N files, validates non-empty, retries 3x.
- Robustness: blocklist (files/network/DROP/DELETE...), 1,000-row cap, empty filter clean exit, null handling.
- Evals: `evals/runner.py` → `evals/reports/test_results.md` (18/18 tests pass across 4 suites: Baseline, Complex, Multi-join, Edge).
- Conversational UI: ChatGPT-style multi-turn chat with inline tables, Matplotlib charts, and execution audit history.

## Resume line
"Multi-CSV ReAct analytics agent (LangGraph-style supervisor, Groq, pandas): join-aware planning over N files, sandboxed code exec with 3x self-repair, rule-based viz; X/Y eval queries pass across 3 domains, live demo."
