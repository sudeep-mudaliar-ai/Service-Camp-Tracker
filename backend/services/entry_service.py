"""Business logic for saving asset entries and duplicate detection."""

from __future__ import annotations

from backend.models.schemas import AssetEntryRequest
from backend.utils.logger import get_logger
from shared.excel_handler import ExcelHandler

logger = get_logger(__name__)

_excel = ExcelHandler()


def is_duplicate_barcode(barcode: str) -> bool:
    """Check whether this barcode was already submitted."""
    return _excel.barcode_exists(barcode)


def save_entry(entry: AssetEntryRequest) -> bool:
    """Persist a form submission to the Excel workbook.

    Returns True when the row was appended, False when the barcode
    already exists (duplicate — nothing written).
    """
    if _excel.barcode_exists(entry.barcode):
        logger.warning("Duplicate barcode rejected: %s", entry.barcode)
        return False

    _excel.append_entry(
        {
            "Barcode": entry.barcode,
            "Serial Number": entry.serial_number,
            "Model": entry.model,
            "Model Category": entry.model_category,
            "Assigned To": entry.assigned_to,
            "Date": entry.date,
            "Time": entry.time,
        }
    )
    logger.info("Entry saved for barcode %s", entry.barcode)
    return True
