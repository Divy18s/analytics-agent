# Analytics Agent v2 — multi-CSV + joins + evals (generic)

Upload 1..N CSVs → shared registry → ask across files (joins auto-detected) → table + chart + insight.

## Agents vs tools (interview-correct)
- Tools (deterministic): `tools/profiler.py` (registry + join candidates), `tools/safe_exec.py` (read-only sandbox, 1000-row cap), `tools/charts.py` (rule chart)
- Agents (LLM): Planner, Coder, Storyteller (`agents/`). Heuristic fallback = runs with no key.
- Supervisor `graph.py`: profile → plan (datasets + join?) → code ↔ execute (max 3) → validate → visualize.

## Run
```powershell
pip install -r requirements.txt
python evals/make_sample_data.py
python evals/run_evals.py
python evals/test_complex_joins.py     # 5-CSV complex join evaluation suite
streamlit run app.py                  # upload complex_data/*.csv or data/*.csv
```
Set `GROQ_API_KEY` in `.env` (or `$env:GROQ_API_KEY`) for LLM planning/coding.

## What it does
- Single-file: groupby/topn/filter/describe on any CSV, auto charts.
- Multi-file: detects shared keys (`join_candidates`), plans `merge(on=, how=left)`, validates non-empty, retries 3x.
- Safety: blocklist (files/network/DROP/DELETE...), `result`-only contract, row cap.
- Evals: `evals/run_evals.py` → `evals/results.md` (pass/fail + chart + plan per query + join shape check).

## Resume line
"Multi-CSV ReAct analytics agent (LangGraph-style supervisor, Groq, pandas): join-aware planning over N files, sandboxed code exec with 3x self-repair, rule-based viz; X/Y eval queries pass across 3 domains, live demo."
