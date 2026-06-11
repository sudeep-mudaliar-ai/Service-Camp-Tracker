"""Central configuration for Service Camp Tracker.

All secrets and environment-specific values are loaded from a `.env`
file (via python-dotenv) or real environment variables. Nothing
sensitive is hardcoded here.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve the project root (the directory containing this `shared/` package)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Load `.env` from the project root, if present. Real environment
# variables always take precedence over the file.
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    """Read an environment variable with optional default and required check."""
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is missing. "
            f"Copy .env.example to .env and fill in the values."
        )
    return value or ""


# ---------- ServiceNow API ----------
SERVICENOW_BASE_URL: str = _get_env(
    "SERVICENOW_BASE_URL", "https://johndeere.service-now.com"
).rstrip("/")
SERVICENOW_API_USERNAME: str = _get_env("SERVICENOW_API_USERNAME")
SERVICENOW_API_PASSWORD: str = _get_env("SERVICENOW_API_PASSWORD")

# Fields requested from the ServiceNow asset table
SERVICENOW_ASSET_FIELDS: str = "serial_number,model_category,model,assigned_to"

# ---------- Excel storage ----------
ONEDRIVE_EXCEL_PATH: Path = Path(
    _get_env("ONEDRIVE_EXCEL_PATH", str(PROJECT_ROOT / "AssetEntries.xlsx"))
)
EXCEL_SHEET_NAME: str = "AssetEntries"
EXCEL_COLUMNS: list[str] = [
    "Barcode",
    "Serial Number",
    "Model",
    "Model Category",
    "Assigned To",
    "Date",
    "Time",
]

# ---------- Backend ----------
BACKEND_HOST: str = _get_env("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT: int = int(_get_env("BACKEND_PORT", "8000"))
BACKEND_BASE_URL: str = _get_env("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# ---------- HTTP behaviour ----------
API_TIMEOUT_SECONDS: float = float(_get_env("API_TIMEOUT_SECONDS", "10"))
API_MAX_RETRIES: int = int(_get_env("API_MAX_RETRIES", "3"))

# ---------- Logging ----------
LOG_LEVEL: str = _get_env("LOG_LEVEL", "INFO").upper()

# ---------- Validation rules ----------
BARCODE_LENGTH: int = 10
