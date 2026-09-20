"""Multi-CSV Analytics Agent: conversational Q&A, multi-table joins, automated tests, and audit."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import get_query_history, run_query
from tools.profiler import profile_all

st.set_page_config(page_title="Analytics Agent (Multi-CSV)", layout="wide", page_icon="📊")
st.title("📊 Analytics Agent — Multi-CSV Q&A & Tests")

# Sidebar file uploader & controls
with st.sidebar:
    st.header("📁 Data Ingestion")
    files = st.file_uploader(
        "Upload 1+ CSVs",
        type=["csv"],
        accept_multiple_files=True,
        help="Upload CSV files (e.g., from complex_data/*.csv or data/*.csv)",
    )
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Shared tabs across the app
t_chat, t_tests, t_audit = st.tabs(["💬 Chat & Analysis", "🧪 Tests", "📜 Query History & Audit"])

# TAB 2: TESTS (Rendered even before upload)
with t_tests:
    st.subheader("🧪 Automated Test Suite & Multi-Join Benchmark")
    report_file = Path(__file__).resolve().parent / "evals" / "reports" / "test_results.md"
    if report_file.exists():
        st.markdown(report_file.read_text(encoding="utf-8"))
    else:
        st.info("Run `python evals/runner.py` in your terminal to generate the consolidated test report.")

# TAB 3: AUDIT & QUERY HISTORY (Human queries only)
with t_audit:
    st.subheader("📜 Human User Query History & Retrieval Audit")
    history = get_query_history()
    if history:
        st.caption(f"Total human queries executed: {len(history)}")
        for h in reversed(history):
            with st.expander(f"[{h.get('timestamp')}] {h.get('question')} ({h.get('mode', 'agent')})"):
                st.write("**Strategy / Plan:**", h.get("plan"))
                st.write("**Retrieval Code Used:**")
                st.code(h.get("code", ""), language="python")
                if h.get("sample"):
                    st.write("**Sample Retrieved Output:**")
                    st.dataframe(pd.DataFrame(h.get("sample")))
                if h.get("trace"):
                    st.write("**Execution Trace:**")
                    st.code("\n".join(h.get("trace", [])))
    else:
        st.info("No human queries executed yet. Ask questions in the Chat tab to view logs here!")

# TAB 1: CONVERSATIONAL CHAT
with t_chat:
    if not files:
        st.info(
            "👈 Please upload 1 or more CSV files in the sidebar to start asking questions! "
            "(Try uploading files from `complex_data/*.csv` or `data/*.csv`)."
        )
    else:
        # Load and profile uploaded datasets
        datasets = {f.name: pd.read_csv(f) for f in files}
        reg = profile_all(datasets)

        # Display dataset metrics
        cols = st.columns(min(len(datasets), 5))
        for (name, df), c in zip(datasets.items(), cols):
            c.metric(name, f"{len(df)} rows × {len(df.columns)} cols")

        with st.expander("🔍 Inspect Schema Registry & Detected Join Candidates"):
            st.json(reg["join_candidates"])

        # Initialize session state for ChatGPT-style messages
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Render past conversation turns
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "user":
                    st.markdown(f"**{msg['content']}**")
                else:
                    st.markdown(msg.get("insight", ""))
                    if "table" in msg and not msg["table"].empty:
                        st.dataframe(msg["table"])
                    if "fig" in msg and msg["fig"] is not None:
                        st.pyplot(msg["fig"])
                    with st.expander("🛠️ Code & Execution Trace"):
                        st.code(msg.get("code", ""), language="python")
                        if msg.get("trace"):
                            st.code("\n".join(msg.get("trace", [])))

        # Chat input box
        prompt = st.chat_input("Ask a question about your uploaded CSVs (e.g. 'total shipping cost by city joining orders and customers')...")
        if prompt:
            # Display user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(f"**{prompt}**")

            # Assistant response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing schema → planning joins → executing code → generating chart..."):
                    out = run_query(datasets, reg, prompt, source="ui")

                st.markdown(out["insight"])
                if not out["table"].empty:
                    st.dataframe(out["table"])
                if out["fig"] is not None:
                    st.pyplot(out["fig"])

                with st.expander("🛠️ Code & Execution Trace"):
                    st.code(out["code"], language="python")
                    st.code("\n".join(out["trace"]))

                # Save turn to session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "insight": out["insight"],
                    "table": out["table"],
                    "fig": out["fig"],
                    "code": out["code"],
                    "trace": out["trace"]
                })
