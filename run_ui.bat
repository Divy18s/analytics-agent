@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
echo Starting Analytics Agent Streamlit UI on http://localhost:8501 ...
.venv\Scripts\python.exe -X utf8 -m streamlit run app.py --server.port 8501
