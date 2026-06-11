# 📦 Service Camp Tracker

An **Asset Entry Management System** for service camps. Scan an asset barcode
with a physical scanner, auto-fetch its details from ServiceNow, review/edit
the values, and store the entry in an Excel workbook that lives in your
OneDrive folder.

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI + Uvicorn |
| Asset lookup | ServiceNow Table API (`alm_asset`) via `requests` |
| Storage | Excel (`AssetEntries` sheet) in a OneDrive-synced folder |
| Excel I/O | pandas + openpyxl |
| Config / secrets | `.env` via python-dotenv |

---

## How it works

```
┌────────────────────┐   barcode = 10 digits   ┌──────────────────┐   Basic Auth    ┌─────────────┐
│ Streamlit frontend │ ──────────────────────▶ │ FastAPI backend  │ ──────────────▶ │ ServiceNow  │
│  (port 8501)       │ ◀────────────────────── │  (port 8000)     │ ◀────────────── │ alm_asset   │
└────────────────────┘   auto-filled fields    └──────────────────┘                 └─────────────┘
          │ SUBMIT                                      │
          ▼                                             ▼
   duplicate check ─────────────────────────▶  AssetEntries.xlsx (OneDrive folder)
```

1. The form has 7 fields: **Barcode, Serial Number, Model, Model Category,
   Assigned To, Date, Time** — all manually editable at all times.
2. The Barcode field is monitored in real time. The instant it contains
   **exactly 10 digits**, the app calls the backend, which queries ServiceNow
   and auto-fills Serial Number, Model, Model Category and Assigned To.
   Values that are not exactly 10 digits are ignored.
3. Date and Time are pre-filled with the current date/time but stay editable.
4. **SUBMIT** is disabled until every field has a value.
5. On SUBMIT the backend reads the Excel sheet and checks for the barcode:
   - **Duplicate** → modal: *"This Barcode has already been submitted. Please check once."* — no row written.
   - **New** → row appended, file saved → modal: *"Entry executed. Proceed.."* — form resets for the next scan.

---

## Project structure

```
Service-Camp-Tracker/
│
├── backend/
│   ├── main.py                     # FastAPI app, health check, error handler
│   ├── routes/
│   │   └── asset_routes.py         # /api/assets, /api/entries, /api/entries/duplicate
│   ├── services/
│   │   ├── servicenow_service.py   # ServiceNow GET with retry + timeout
│   │   └── entry_service.py        # save + duplicate-check business logic
│   ├── models/
│   │   └── schemas.py              # Pydantic request/response models
│   ├── utils/
│   │   ├── logger.py               # console + rotating-file logging
│   │   └── validators.py           # barcode validation
│   └── requirements.txt
│
├── frontend/
│   ├── app.py                      # Streamlit UI
│   └── requirements.txt
│
├── shared/
│   ├── config.py                   # .env loading, all settings
│   └── excel_handler.py            # create/read/append Excel with lock retries
│
├── .env.example                    # template — copy to .env
├── requirements.txt                # combined deps
├── run.bat                         # Windows: start backend + frontend
├── run.sh                          # Linux/macOS: start backend + frontend
└── README.md
```

---

## Installation

**Prerequisites:** Python **3.11+**, and (for OneDrive sync) the OneDrive
desktop client signed in on the machine.

```bash
# 1. Clone the repository
git clone https://github.com/sudeep-mudaliar-ai/Service-Camp-Tracker.git
cd Service-Camp-Tracker

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Environment setup

```bash
# Copy the template and edit it
copy .env.example .env        # Windows
cp .env.example .env          # Linux/macOS
```

Then open `.env` and fill in:

| Variable | Description |
|---|---|
| `SERVICENOW_BASE_URL` | ServiceNow instance, e.g. `https://johndeere.service-now.com` |
| `SERVICENOW_API_USERNAME` | ServiceNow integration user |
| `SERVICENOW_API_PASSWORD` | ServiceNow integration password |
| `ONEDRIVE_EXCEL_PATH` | Full path to the workbook **inside your OneDrive folder**, e.g. `C:/Users/you/OneDrive/AssetEntries.xlsx` |
| `BACKEND_BASE_URL` | Where the frontend reaches the backend (default `http://127.0.0.1:8000`) |
| `API_TIMEOUT_SECONDS` | ServiceNow call timeout (default 10) |
| `API_MAX_RETRIES` | Retries for transient ServiceNow failures (default 3) |

> 🔐 **Never commit `.env`** — it contains credentials and is git-ignored.

---

## Running the application

### One-shot (Windows)

```bat
run.bat
```

This opens two terminal windows: the backend on port **8000** and the
frontend on port **8501**, then opens the UI in your browser.

### Manual

**Backend (terminal 1):**

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Interactive API docs: <http://127.0.0.1:8000/docs> · Health: <http://127.0.0.1:8000/health>

**Frontend (terminal 2):**

```bash
streamlit run frontend/app.py
```

UI: <http://localhost:8501>

---

## API endpoints

| Method | Path | Purpose | Notable status codes |
|---|---|---|---|
| `GET` | `/api/assets/{barcode}` | Fetch asset details from ServiceNow | `200`, `422` invalid barcode, `502` ServiceNow error |
| `GET` | `/api/entries/duplicate/{barcode}` | Check if barcode already submitted | `200`, `422`, `503` Excel locked |
| `POST` | `/api/entries` | Validate + duplicate-check + append row | `201` saved, `409` duplicate, `422` validation, `503` Excel locked |
| `GET` | `/health` | Liveness probe | `200` |

---

## How barcode scanning works

Physical USB barcode scanners act as **keyboards**: they "type" the barcode
characters very quickly and usually send an Enter keystroke at the end.

1. Click into the **Barcode** field (or just leave focus there — it is the
   first field on the page).
2. Scan the asset tag. The scanner types the digits; Enter commits the field.
3. Streamlit reruns on the change; the app sees the field now holds exactly
   **10 digits** and automatically calls the backend → ServiceNow.
4. A spinner shows during the lookup; on success a toast appears and Serial
   Number, Model, Model Category and Assigned To are filled in (still editable).
5. Anything that is **not** exactly 10 digits (too short, too long, letters)
   is ignored for auto-fetch and flagged with an inline validation message.

> Tip: configure your scanner to append a carriage return (CR / Enter) suffix
> — most are shipped that way by default.

---

## OneDrive setup instructions

The app writes a **local** Excel file; the OneDrive desktop client does the
cloud syncing. No Microsoft Graph credentials are needed.

1. Install and sign in to the **OneDrive desktop client** (preinstalled on
   Windows 10/11).
2. Find your local OneDrive folder, e.g. `C:\Users\<you>\OneDrive` or
   `C:\Users\<you>\OneDrive - <Company>`.
3. Set `ONEDRIVE_EXCEL_PATH` in `.env` to a path inside that folder, using
   forward slashes, e.g.:
   `ONEDRIVE_EXCEL_PATH=C:/Users/you/OneDrive/ServiceCamp/AssetEntries.xlsx`
4. Make sure the folder is set to **"Always keep on this device"**
   (right-click → settings) so writes never hit a cloud-only placeholder.

## Excel file setup instructions

Nothing to do manually — on first run the app **creates the workbook
automatically** with:

- Sheet name: `AssetEntries`
- Columns: `Barcode`, `Serial Number`, `Model`, `Model Category`,
  `Assigned To`, `Date`, `Time`

If you pre-create the file yourself, keep that exact sheet name and header
row. Avoid keeping the file open in Excel while submitting entries — the app
retries on file locks, but a long-held lock will surface as a "file is
locked" error.

---

## Built-in robustness features

- **Retry with exponential backoff** for ServiceNow calls (429/5xx, network).
- **Timeout handling** on every outbound HTTP call.
- **Excel lock handling** — read/open/save retried up to 5× when OneDrive or
  Excel briefly locks the file; clean `503` if it stays locked.
- **Rapid-submission guard** — submit button disabled while saving plus a
  2-second cooldown window.
- **Auto-reset & refresh** after each successful submission.
- **Toast notifications** for fetch results, resets and submissions.
- **Inline validation messages** for partial/invalid barcodes and empty fields.
- **Logging** to console and `logs/backend.log` (rotating).

---

## Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| `Could not reach the backend at http://127.0.0.1:8000` | Backend not running. Start it with `python -m uvicorn backend.main:app --port 8000`, check `/health`. |
| `ServiceNow authentication failed (401)` | Wrong `SERVICENOW_API_USERNAME` / `SERVICENOW_API_PASSWORD` in `.env`. |
| `Asset lookup timed out` | ServiceNow unreachable from your network (VPN/proxy?). Increase `API_TIMEOUT_SECONDS`. |
| `No asset found in ServiceNow for this barcode` | The asset tag doesn't exist in `alm_asset`. Fill the fields manually. |
| `file is locked` / `503` on submit | The workbook is open in Excel or mid-sync. Close Excel, wait for OneDrive sync, retry. |
| Excel file not appearing in OneDrive cloud | Path is outside the synced folder, or sync paused. Verify `ONEDRIVE_EXCEL_PATH` and the OneDrive tray icon. |
| SUBMIT stays disabled | One or more fields are empty, or the barcode isn't exactly 10 digits. |
| Scanner fills the wrong field | Click into the Barcode field before scanning; ensure scanner sends an Enter suffix. |
| `Required environment variable ... is missing` | You haven't created `.env`. Copy `.env.example` and fill it in. |
| Port already in use | Change `BACKEND_PORT` in `.env` (and `BACKEND_BASE_URL`), or `streamlit run frontend/app.py --server.port 8502`. |

---

## Security notes

- Credentials live **only** in `.env` (git-ignored). Nothing is hardcoded.
- The backend binds to `127.0.0.1` by default — it is not exposed on the LAN.
- Rotate the ServiceNow integration password periodically and scope the
  integration user to read-only access on `alm_asset`.
