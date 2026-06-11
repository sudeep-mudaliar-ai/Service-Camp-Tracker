"""Pydantic request/response models for the Service Camp Tracker API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from shared import config


class AssetDetails(BaseModel):
    """Asset fields fetched from ServiceNow for a barcode."""

    serial_number: str = ""
    model: str = ""
    model_category: str = ""
    assigned_to: str = ""


class AssetFetchResponse(BaseModel):
    """Response for GET /api/assets/{barcode}."""

    found: bool
    barcode: str
    asset: AssetDetails | None = None
    message: str = ""


class DuplicateCheckResponse(BaseModel):
    """Response for GET /api/entries/duplicate/{barcode}."""

    barcode: str
    is_duplicate: bool


class AssetEntryRequest(BaseModel):
    """Payload for POST /api/entries — one form submission."""

    barcode: str = Field(..., description="Exactly 10 digits")
    serial_number: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    model_category: str = Field(..., min_length=1)
    assigned_to: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1, description="Entry date, e.g. 2026-06-11")
    time: str = Field(..., min_length=1, description="Entry time, e.g. 14:35:02")

    @field_validator("barcode")
    @classmethod
    def barcode_must_be_ten_digits(cls, value: str) -> str:
        value = value.strip()
        if len(value) != config.BARCODE_LENGTH or not value.isdigit():
            raise ValueError(
                f"Barcode must contain exactly {config.BARCODE_LENGTH} digits."
            )
        return value

    @field_validator(
        "serial_number", "model", "model_category", "assigned_to", "date", "time"
    )
    @classmethod
    def strip_and_require(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be empty.")
        return value


class SaveEntryResponse(BaseModel):
    """Response for POST /api/entries."""

    success: bool
    duplicate: bool = False
    message: str


class ErrorResponse(BaseModel):
    """Standard error body returned by exception handlers."""

    detail: str
