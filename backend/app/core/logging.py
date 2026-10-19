"""Structured, secret-safe logging configuration."""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

_REDACT_KEYS = {"authorization", "api_key", "apikey", "password", "token", "secret"}


class RedactingFilter(logging.Filter):
    """Best-effort redaction of sensitive values from log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            msg = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        lowered = msg.lower()
        for key in _REDACT_KEYS:
            if key in lowered:
                record.msg = "[redacted log line containing sensitive key]"
                record.args = ()
                break
        return True


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Tame noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "asyncio", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
