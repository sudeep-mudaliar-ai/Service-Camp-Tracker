"""API routes: asset lookup, entry saving, duplicate validation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import (
    AssetEntryRequest,
    AssetFetchResponse,
    DuplicateCheckResponse,
    ErrorResponse,
    SaveEntryResponse,
)
from backend.services import entry_service
from backend.services.servicenow_service import ServiceNowError, fetch_asset_details
from backend.utils.logger import get_logger
from backend.utils.validators import is_valid_barcode
from shared.excel_handler import ExcelLockedError

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["assets"])


def _require_valid_barcode(barcode: str) -> str:
    """Reject any barcode that is not exactly 10 digits."""
    barcode = barcode.strip()
    if not is_valid_barcode(barcode):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Barcode must contain exactly 10 digits.",
        )
    return barcode


@router.get(
    "/assets/{barcode}",
    response_model=AssetFetchResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    summary="Fetch asset details from ServiceNow by barcode",
)
def get_asset(barcode: str) -> AssetFetchResponse:
    """Look up serial number, model, model category and assignee for a barcode."""
    barcode = _require_valid_barcode(barcode)
    try:
        asset = fetch_asset_details(barcode)
    except ServiceNowError as error:
        logger.error("Asset fetch failed for %s: %s", barcode, error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)
        ) from error

    if asset is None:
        return AssetFetchResponse(
            found=False,
            barcode=barcode,
            message="No asset found in ServiceNow for this barcode.",
        )
    return AssetFetchResponse(found=True, barcode=barcode, asset=asset, message="OK")


@router.get(
    "/entries/duplicate/{barcode}",
    response_model=DuplicateCheckResponse,
    responses={422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Check whether a barcode already exists in the Excel sheet",
)
def check_duplicate(barcode: str) -> DuplicateCheckResponse:
    """Return whether this barcode has already been submitted."""
    barcode = _require_valid_barcode(barcode)
    try:
        duplicate = entry_service.is_duplicate_barcode(barcode)
    except ExcelLockedError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    return DuplicateCheckResponse(barcode=barcode, is_duplicate=duplicate)


@router.post(
    "/entries",
    response_model=SaveEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Save a form submission to the Excel workbook",
)
def save_entry(entry: AssetEntryRequest) -> SaveEntryResponse:
    """Validate, duplicate-check and append the entry to the Excel sheet."""
    try:
        saved = entry_service.save_entry(entry)
    except ExcelLockedError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error

    if not saved:
        # Duplicate barcode — surface as 409 Conflict so the frontend
        # can show the dedicated duplicate modal.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Barcode has already been submitted. Please check once.",
        )
    return SaveEntryResponse(success=True, message="Entry executed. Proceed..")
