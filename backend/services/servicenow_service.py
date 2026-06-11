"""ServiceNow integration: fetch asset details for a barcode (asset tag).

Uses `requests` with Basic Authentication, a configurable timeout, and
automatic retries with exponential backoff for transient failures.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from backend.models.schemas import AssetDetails
from backend.utils.logger import get_logger
from shared import config

logger = get_logger(__name__)


class ServiceNowError(Exception):
    """Raised when the ServiceNow API call fails after all retries."""


def _build_session() -> requests.Session:
    """Create a requests session with retry/backoff on transient errors."""
    retry_policy = Retry(
        total=config.API_MAX_RETRIES,
        backoff_factor=0.5,  # 0.5s, 1s, 2s ...
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_policy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = _build_session()


def fetch_asset_details(barcode: str) -> AssetDetails | None:
    """Look up asset details in ServiceNow by asset tag (barcode).

    Returns AssetDetails when a record is found, None when no record
    matches, and raises ServiceNowError on communication problems.
    """
    if not config.SERVICENOW_API_USERNAME or not config.SERVICENOW_API_PASSWORD:
        raise ServiceNowError(
            "ServiceNow credentials are not configured. "
            "Set SERVICENOW_API_USERNAME and SERVICENOW_API_PASSWORD in .env."
        )

    url = f"{config.SERVICENOW_BASE_URL}/api/now/table/alm_asset"
    params = {
        "sysparm_display_value": "true",
        "sysparm_exclude_reference_link": "true",
        "sysparm_limit": "1",
        "sysparm_offset": "0",
        "asset_tag": barcode,
        "sysparm_fields": config.SERVICENOW_ASSET_FIELDS,
    }

    logger.info("Fetching asset details from ServiceNow for barcode %s", barcode)
    try:
        response = _session.get(
            url,
            params=params,
            auth=HTTPBasicAuth(
                config.SERVICENOW_API_USERNAME, config.SERVICENOW_API_PASSWORD
            ),
            headers={"Accept": "application/json"},
            timeout=config.API_TIMEOUT_SECONDS,
        )
    except requests.Timeout as error:
        logger.error("ServiceNow request timed out for barcode %s", barcode)
        raise ServiceNowError(
            f"ServiceNow request timed out after {config.API_TIMEOUT_SECONDS}s."
        ) from error
    except requests.RequestException as error:
        logger.error("ServiceNow request failed: %s", error)
        raise ServiceNowError(f"Could not reach ServiceNow: {error}") from error

    if response.status_code == 401:
        raise ServiceNowError("ServiceNow authentication failed (401). Check credentials.")
    if not response.ok:
        raise ServiceNowError(
            f"ServiceNow returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        records = response.json().get("result", [])
    except ValueError as error:
        raise ServiceNowError("ServiceNow returned a non-JSON response.") from error

    if not records:
        logger.info("No ServiceNow asset found for barcode %s", barcode)
        return None

    record = records[0]
    # ServiceNow reference fields may come back as dicts when links are
    # included; with sysparm_exclude_reference_link=true they are plain
    # strings, but we defend against both shapes.
    def _as_text(value: object) -> str:
        if isinstance(value, dict):
            return str(value.get("display_value", "")).strip()
        return str(value or "").strip()

    details = AssetDetails(
        serial_number=_as_text(record.get("serial_number")),
        model=_as_text(record.get("model")),
        model_category=_as_text(record.get("model_category")),
        assigned_to=_as_text(record.get("assigned_to")),
    )
    logger.info("Asset found for barcode %s: serial=%s", barcode, details.serial_number)
    return details
