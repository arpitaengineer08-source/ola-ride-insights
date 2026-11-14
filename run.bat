@echo off
REM One-click launcher for Windows
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate
pip install -q -r requirements.txt
python -m streamlit run app/streamlit_app.py
