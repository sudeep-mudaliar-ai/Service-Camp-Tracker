@echo off
REM ============================================================
REM Service Camp Tracker - Windows launcher
REM Starts the FastAPI backend and the Streamlit frontend.
REM Run from the project root: run.bat
REM ============================================================

cd /d "%~dp0"

IF NOT EXIST ".env" (
    echo [WARN] .env file not found. Copy .env.example to .env and fill in values.
)

echo Starting FastAPI backend on http://127.0.0.1:8000 ...
start "ServiceCampTracker-Backend" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

REM Give the backend a moment to boot before the UI starts polling it
timeout /t 3 /nobreak >nul

echo Starting Streamlit frontend on http://localhost:8501 ...
start "ServiceCampTracker-Frontend" cmd /k "python -m streamlit run frontend/app.py"

echo Both services launched. Close their windows to stop them.
