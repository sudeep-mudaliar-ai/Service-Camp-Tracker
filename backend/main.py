"""Service Camp Tracker — FastAPI backend entry point.

Run with:
    uvicorn backend.main:app --host 127.0.0.1 --port 8000
or simply:
    python -m backend.main
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.routes.asset_routes import router as asset_router
from backend.utils.logger import get_logger, setup_logging
from shared import config
from shared.excel_handler import ExcelHandler

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Service Camp Tracker API",
    description="Asset Entry Management System backend (ServiceNow + Excel/OneDrive).",
    version="1.0.0",
)

app.include_router(asset_router)


@app.on_event("startup")
def on_startup() -> None:
    """Make sure the Excel workbook exists before serving requests."""
    logger.info("Backend starting; Excel path: %s", config.ONEDRIVE_EXCEL_PATH)
    try:
        ExcelHandler().ensure_file_exists()
    except Exception:  # noqa: BLE001 — log and continue; routes retry later
        logger.exception("Could not create/verify Excel workbook at startup")


@app.get("/health", tags=["health"], summary="Liveness probe")
def health() -> dict[str, str]:
    """Simple health check used by the frontend and run scripts."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so unexpected errors return clean JSON instead of stack traces."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Check backend logs for details."},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=config.BACKEND_HOST,
        port=config.BACKEND_PORT,
        reload=False,
    )
