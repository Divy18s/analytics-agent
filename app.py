"""Multi-CSV analytics app: upload 1..N CSVs, join-aware Q&A, evals tab."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import run_query
from tools.profiler import profile_all

st.set_page_config(page_title="Analytics Agent (multi-CSV)", layout="wide")
st.title("Analytics Agent — multi-CSV + joins + evals")

files = st.file_uploader("Upload 1+ CSVs", type=["csv"], accept_multiple_files=True)
if not files:
    st.info("Upload e.g. orders.csv + customers.csv (share a key like cid), then ask join questions.")
    st.stop()

datasets = {f.name: pd.read_csv(f) for f in files}
reg = profile_all(datasets)
c = st.columns(len(datasets))
for (name, df), col in zip(datasets.items(), c):
    col.metric(name, f"{len(df)} rows x {len(df.columns)} cols")
with st.expander("Registry + join candidates"):
    st.json(reg["join_candidates"])

t1, t2 = st.tabs(["Ask", "Evals"])
with t1:
    q = st.text_input("Question", "total amt by city joining orders and customers?")
    if st.button("Run") and q:
        with st.spinner("plan → code → execute → validate → chart…"):
            out = run_query(datasets, reg, q)
        st.write(out["insight"])
        st.dataframe(out["table"])
        st.pyplot(out["fig"])
        with st.expander("Trace"):
            st.code("\n".join(out["trace"]))
            st.code(out["code"], language="python")
with t2:
    st.markdown("Run `python evals/run_evals.py` (uses `data/*.csv`), then results appear in `evals/results.md`.")
    p = Path(__file__).resolve().parent / "evals" / "results.md"
    if p.exists():
        st.markdown(p.read_text())
