"""Multi-CSV analytics app: upload 1..N CSVs, join-aware Q&A, evals tab."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import get_query_history, run_query
from tools.profiler import profile_all

st.set_page_config(page_title="Analytics Agent (multi-CSV)", layout="wide")
st.title("Analytics Agent — multi-CSV + joins + evals")

files = st.file_uploader("Upload 1+ CSVs (e.g. from complex_data/*.csv)", type=["csv"], accept_multiple_files=True)
if not files:
    st.info("Upload CSV files (e.g., from `complex_data/*.csv` or `data/*.csv`), then ask join questions.")
    
    # Still show evaluation and query history tabs even before upload
    t_eval, t_hist = st.tabs(["Complex Evals & Comparisons", "Query History & Retrieval Audit"])
    with t_eval:
        p_complex = Path(__file__).resolve().parent / "evals" / "complex_test_results.md"
        if p_complex.exists():
            st.markdown(p_complex.read_text(encoding="utf-8"))
        else:
            st.info("Run `python evals/test_complex_joins.py` to generate the complex join report.")
    with t_hist:
        history = get_query_history()
        if history:
            st.subheader(f"Total Logged Queries: {len(history)}")
            for h in reversed(history):
                with st.expander(f"[{h.get('timestamp')}] {h.get('question')} ({h.get('mode', 'agent')})"):
                    st.write("**Plan:**", h.get("plan"))
                    st.write("**Retrieval Code Used:**")
                    st.code(h.get("code", ""), language="python")
                    if h.get("sample"):
                        st.write("**Data Sample:**")
                        st.dataframe(pd.DataFrame(h.get("sample")))
        else:
            st.write("No queries executed yet.")
    st.stop()

datasets = {f.name: pd.read_csv(f) for f in files}
reg = profile_all(datasets)
c = st.columns(len(datasets))
for (name, df), col in zip(datasets.items(), c):
    col.metric(name, f"{len(df)} rows x {len(df.columns)} cols")
with st.expander("Registry + join candidates"):
    st.json(reg["join_candidates"])

t1, t2, t3 = st.tabs(["Ask", "Complex Evals & Comparisons", "Query History & Retrieval Audit"])
with t1:
    q = st.text_input("Question", "total shipping cost by city joining orders and customers")
    if st.button("Run") and q:
        with st.spinner("plan → code → execute → validate → chart…"):
            out = run_query(datasets, reg, q)
        st.write(out["insight"])
        st.dataframe(out["table"])
        st.pyplot(out["fig"])
        with st.expander("Retrieval Code & Trace"):
            st.write("**Code Used to Retrieve Data:**")
            st.code(out["code"], language="python")
            st.write("**Execution Trace:**")
            st.code("\n".join(out["trace"]))
with t2:
    p_complex = Path(__file__).resolve().parent / "evals" / "complex_test_results.md"
    if p_complex.exists():
        st.markdown(p_complex.read_text(encoding="utf-8"))
    else:
        st.markdown("Run `python evals/test_complex_joins.py` to generate the complex join comparison report.")
with t3:
    history = get_query_history()
    if history:
        st.subheader(f"Total Logged Queries: {len(history)}")
        for h in reversed(history):
            with st.expander(f"[{h.get('timestamp')}] {h.get('question')} ({h.get('mode', 'agent')})"):
                st.write("**Plan:**", h.get("plan"))
                st.write("**Retrieval Code Used:**")
                st.code(h.get("code", ""), language="python")
                if h.get("sample"):
                    st.write("**Data Sample:**")
                    st.dataframe(pd.DataFrame(h.get("sample")))
    else:
        st.write("No queries executed yet.")
