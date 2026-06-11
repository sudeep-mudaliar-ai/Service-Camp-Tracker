"""Application-wide logging setup.

Logs to both stdout and a rotating file under `logs/`.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from shared import config

_LOG_DIR = config.PROJECT_ROOT / "logs"
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    """Configure root logging once for the whole backend process."""
    root = logging.getLogger()
    if root.handlers:  # already configured (e.g. uvicorn reload)
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / "backend.log"

    formatter = logging.Formatter(_LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root.setLevel(config.LOG_LEVEL)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor used across backend modules."""
    return logging.getLogger(name)
