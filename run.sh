#!/usr/bin/env bash
# ============================================================
# Service Camp Tracker - Linux/macOS launcher
# Starts the FastAPI backend and the Streamlit frontend.
# Run from the project root: ./run.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
    echo "[WARN] .env file not found. Copy .env.example to .env and fill in values."
fi

echo "Starting FastAPI backend on http://127.0.0.1:8000 ..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

# Give the backend a moment to boot before the UI starts polling it
sleep 3

echo "Starting Streamlit frontend on http://localhost:8501 ..."
python -m streamlit run frontend/app.py
