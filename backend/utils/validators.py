"""Reusable validation helpers."""

from __future__ import annotations

from shared import config


def is_valid_barcode(barcode: str) -> bool:
    """A valid barcode is exactly 10 characters and digits only."""
    barcode = (barcode or "").strip()
    return len(barcode) == config.BARCODE_LENGTH and barcode.isdigit()
