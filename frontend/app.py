"""Service Camp Tracker — Streamlit frontend.

Asset Entry Management System UI:
- Single form with 7 editable fields.
- Real-time barcode monitoring: when the Barcode field contains exactly
  10 digits (typed or filled by a physical scanner), asset details are
  fetched automatically from the FastAPI backend and auto-filled.
- SUBMIT stays disabled until every field has a value.
- Duplicate barcodes are rejected with a popup modal; successful saves
  show a success modal and reset the form.

Run with:
    streamlit run frontend/app.py
"""

from __future__ import annotations

import os
import time as time_module
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
load_dotenv()  # picks up .env from the project root / working directory

BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TIMEOUT_SECONDS: float = float(os.getenv("API_TIMEOUT_SECONDS", "10"))
BARCODE_LENGTH: int = 10
SUBMIT_COOLDOWN_SECONDS: float = 2.0  # guards against rapid double submits

FIELD_KEYS = (
    "barcode",
    "serial_number",
    "model",
    "model_category",
    "assigned_to",
    "entry_date",
    "entry_time",
)

st.set_page_config(
    page_title="Service Camp Tracker",
    page_icon="📦",
    layout="centered",
)


# ----------------------------------------------------------------------
# Session-state helpers
# ----------------------------------------------------------------------
def init_session_state() -> None:
    """Create all session-state keys on first load."""
    now = datetime.now()
    defaults: dict[str, object] = {
        "barcode": "",
        "serial_number": "",
        "model": "",
        "model_category": "",
        "assigned_to": "",
        "entry_date": now.date(),
        "entry_time": now.time().replace(microsecond=0),
        "last_fetched_barcode": "",   # avoids re-fetching the same barcode
        "last_submit_ts": 0.0,        # rapid-submission guard
        "submitting": False,
        "pending_reset": False,
        "fetch_error": "",
        "fetch_notice": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_form() -> None:
    """Clear all fields and refresh date/time to the current moment."""
    now = datetime.now()
    st.session_state["barcode"] = ""
    st.session_state["serial_number"] = ""
    st.session_state["model"] = ""
    st.session_state["model_category"] = ""
    st.session_state["assigned_to"] = ""
    st.session_state["entry_date"] = now.date()
    st.session_state["entry_time"] = now.time().replace(microsecond=0)
    st.session_state["last_fetched_barcode"] = ""
    st.session_state["fetch_error"] = ""
    st.session_state["fetch_notice"] = ""


def is_valid_barcode(value: str) -> bool:
    """Valid barcode = exactly 10 characters, digits only."""
    value = (value or "").strip()
    return len(value) == BARCODE_LENGTH and value.isdigit()


def all_fields_filled() -> bool:
    """SUBMIT enable condition: every field must contain a value."""
    text_ok = all(
        str(st.session_state.get(key, "")).strip()
        for key in ("barcode", "serial_number", "model", "model_category", "assigned_to")
    )
    date_ok = st.session_state.get("entry_date") is not None
    time_ok = st.session_state.get("entry_time") is not None
    return text_ok and date_ok and time_ok


# ----------------------------------------------------------------------
# Backend calls
# ----------------------------------------------------------------------
def fetch_asset_from_backend(barcode: str) -> None:
    """Call the FastAPI backend to auto-fill asset details for a barcode.

    Runs in the main script body (before widgets render) so it can
    safely write into the widget session-state keys.
    """
    st.session_state["fetch_error"] = ""
    st.session_state["fetch_notice"] = ""
    try:
        with st.spinner(f"Fetching asset details for barcode {barcode}..."):
            response = requests.get(
                f"{BACKEND_BASE_URL}/api/assets/{barcode}",
                timeout=API_TIMEOUT_SECONDS + 5,
            )
        if response.ok:
            payload = response.json()
            if payload.get("found") and payload.get("asset"):
                asset = payload["asset"]
                st.session_state["serial_number"] = asset.get("serial_number", "")
                st.session_state["model"] = asset.get("model", "")
                st.session_state["model_category"] = asset.get("model_category", "")
                st.session_state["assigned_to"] = asset.get("assigned_to", "")
                st.toast("Asset details fetched ✔", icon="✅")
            else:
                st.session_state["fetch_notice"] = (
                    "No asset found in ServiceNow for this barcode. "
                    "You can fill the fields manually."
                )
                st.toast("No asset found for this barcode", icon="⚠️")
        else:
            detail = ""
            try:
                detail = response.json().get("detail", "")
            except ValueError:
                detail = response.text[:200]
            st.session_state["fetch_error"] = (
                f"Asset lookup failed (HTTP {response.status_code}): {detail}"
            )
    except requests.Timeout:
        st.session_state["fetch_error"] = (
            "Asset lookup timed out. Check the backend and ServiceNow connectivity."
        )
    except requests.RequestException as error:
        st.session_state["fetch_error"] = (
            f"Could not reach the backend at {BACKEND_BASE_URL}: {error}"
        )


def submit_entry() -> tuple[str, str]:
    """POST the form to the backend.

    Returns a (status, message) tuple where status is one of
    'success', 'duplicate' or 'error'.
    """
    payload = {
        "barcode": str(st.session_state["barcode"]).strip(),
        "serial_number": str(st.session_state["serial_number"]).strip(),
        "model": str(st.session_state["model"]).strip(),
        "model_category": str(st.session_state["model_category"]).strip(),
        "assigned_to": str(st.session_state["assigned_to"]).strip(),
        "date": st.session_state["entry_date"].strftime("%Y-%m-%d"),
        "time": st.session_state["entry_time"].strftime("%H:%M:%S"),
    }
    try:
        response = requests.post(
            f"{BACKEND_BASE_URL}/api/entries",
            json=payload,
            timeout=API_TIMEOUT_SECONDS + 5,
        )
    except requests.Timeout:
        return "error", "Save request timed out. Please try again."
    except requests.RequestException as error:
        return "error", f"Could not reach the backend at {BACKEND_BASE_URL}: {error}"

    if response.status_code == 201:
        return "success", "Entry executed. Proceed.."
    if response.status_code == 409:
        return "duplicate", "This Barcode has already been submitted. Please check once."

    try:
        detail = response.json().get("detail", response.text[:200])
    except ValueError:
        detail = response.text[:200]
    return "error", f"Save failed (HTTP {response.status_code}): {detail}"


# ----------------------------------------------------------------------
# Popup modals
# ----------------------------------------------------------------------
@st.dialog("✅ Success")
def success_modal() -> None:
    """Shown after a successful save; closing it resets the form."""
    st.success("Entry executed. Proceed..")
    if st.button("OK", use_container_width=True, type="primary"):
        st.session_state["pending_reset"] = True
        st.rerun()


@st.dialog("⚠️ Duplicate Barcode")
def duplicate_modal() -> None:
    """Shown when the barcode already exists in the Excel sheet."""
    st.warning("This Barcode has already been submitted. Please check once.")
    if st.button("OK", use_container_width=True):
        st.rerun()


# ----------------------------------------------------------------------
# Main app
# ----------------------------------------------------------------------
def main() -> None:
    init_session_state()

    # Apply a deferred form reset BEFORE widgets are instantiated —
    # Streamlit forbids writing widget keys after their widget renders.
    if st.session_state["pending_reset"]:
        st.session_state["pending_reset"] = False
        reset_form()
        st.toast("Form reset — ready for the next scan", icon="🔄")

    # ------------------------------------------------------------------
    # Real-time barcode monitoring: every rerun (each keystroke/scan
    # triggers one) we check the barcode. The moment it becomes exactly
    # 10 digits and differs from the last fetched value, auto-fetch.
    # Values that are not exactly 10 digits are ignored.
    # ------------------------------------------------------------------
    current_barcode = str(st.session_state.get("barcode", "")).strip()
    if (
        is_valid_barcode(current_barcode)
        and current_barcode != st.session_state["last_fetched_barcode"]
    ):
        st.session_state["last_fetched_barcode"] = current_barcode
        fetch_asset_from_backend(current_barcode)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    st.title("📦 Service Camp Tracker")
    st.caption("Asset Entry Management System — scan a barcode or type one to begin.")

    # Surface any fetch problems from this or the previous rerun
    if st.session_state["fetch_error"]:
        st.error(st.session_state["fetch_error"])
    if st.session_state["fetch_notice"]:
        st.info(st.session_state["fetch_notice"])

    # ------------------------------------------------------------------
    # Form fields (all editable; intentionally NOT inside st.form so we
    # get a rerun per change for real-time barcode detection)
    # ------------------------------------------------------------------
    st.text_input(
        "Barcode *",
        key="barcode",
        max_chars=BARCODE_LENGTH,
        placeholder="Scan or type a 10-digit barcode",
        help="Exactly 10 digits. Asset details auto-fill when valid.",
    )

    # Inline barcode validation message
    if current_barcode and not is_valid_barcode(current_barcode):
        if not current_barcode.isdigit():
            st.warning("Barcode must contain only digits.")
        else:
            st.info(
                f"Barcode is {len(current_barcode)}/{BARCODE_LENGTH} digits — "
                "auto-fetch triggers at exactly 10."
            )

    col_left, col_right = st.columns(2)
    with col_left:
        st.text_input("Serial Number *", key="serial_number")
        st.text_input("Model Category *", key="model_category")
        st.date_input("Date *", key="entry_date")
    with col_right:
        st.text_input("Model *", key="model")
        st.text_input("Assigned To *", key="assigned_to")
        st.time_input("Time *", key="entry_time", step=60)

    # ------------------------------------------------------------------
    # SUBMIT — disabled until every field is filled; also disabled
    # while a submission is in flight (rapid-click protection).
    # ------------------------------------------------------------------
    ready = all_fields_filled() and is_valid_barcode(current_barcode)

    if not ready:
        if all_fields_filled() and not is_valid_barcode(current_barcode):
            st.warning("Barcode must be exactly 10 digits to submit.")
        else:
            st.info("Fill in all fields to enable SUBMIT.")

    submit_clicked = st.button(
        "SUBMIT",
        type="primary",
        use_container_width=True,
        disabled=not ready or st.session_state["submitting"],
    )

    if submit_clicked:
        # Cooldown guard: ignore submits fired within the cooldown window
        now_ts = time_module.time()
        if now_ts - st.session_state["last_submit_ts"] < SUBMIT_COOLDOWN_SECONDS:
            st.toast("Please wait — previous submission still processing", icon="⏳")
            return
        st.session_state["last_submit_ts"] = now_ts
        st.session_state["submitting"] = True

        with st.spinner("Saving entry..."):
            status_code, message = submit_entry()

        st.session_state["submitting"] = False

        if status_code == "success":
            st.toast(message, icon="✅")
            success_modal()
        elif status_code == "duplicate":
            st.toast(message, icon="⚠️")
            duplicate_modal()
        else:
            st.error(message)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    st.divider()
    st.caption(
        f"Backend: {BACKEND_BASE_URL} · Entries are stored in the Excel "
        "workbook configured via ONEDRIVE_EXCEL_PATH."
    )


if __name__ == "__main__":
    # `streamlit run` executes this script with __name__ == "__main__"
    main()
