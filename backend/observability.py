"""Observability — JSON logging + optional Sentry.

Two env knobs:

* `ORGON_JSON_LOGS=1`  — switch the root logger to a JSON formatter
                         (one record per line, easy to ingest by Loki /
                         Datadog / CloudWatch). Default off — humans
                         debugging locally want plain text.
* `SENTRY_DSN=https://…` — initialize Sentry SDK with FastAPI + asyncio
                            integrations. Default off (no DSN → no
                            outbound traffic).

Designed so calling `configure_observability()` is safe on every boot:
when the relevant env is missing, the function is a no-op.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sys
from typing import Optional

logger = logging.getLogger("orgon.observability")

_RESERVED_LOGRECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter — one object per line."""

    def format(self, record: logging.LogRecord) -> str:
        # ISO-8601 with milliseconds; %f from strftime is unsupported, so
        # we go through datetime.fromtimestamp instead.
        ts = dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc)
        payload: dict = {
            "ts":     ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z",
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Include any custom attrs added via `logger.info("...", extra={...})`.
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Apply JSON formatter when ORGON_JSON_LOGS is truthy."""
    if os.getenv("ORGON_JSON_LOGS", "").lower() not in {"1", "true", "yes"}:
        return  # keep the default plain formatter from main.py
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logger.info("JSON logging enabled (ORGON_JSON_LOGS=1)")


def configure_sentry() -> Optional[object]:
    """Initialize Sentry SDK if SENTRY_DSN is set. Returns the SDK module
    (or None) so callers can skip Sentry-specific decorators when off."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return None
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry-sdk is not installed — skipping init")
        return None

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ORGON_ENV", "development"),
        release=os.getenv("ORGON_RELEASE") or None,
        send_default_pii=False,  # never send user emails / IPs by default
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
        integrations=[
            AsyncioIntegration(),
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
        ],
    )
    logger.info("Sentry initialized (env=%s)", os.getenv("ORGON_ENV", "development"))
    return sentry_sdk


def configure_observability() -> None:
    """One call at app startup — applies whatever env says is enabled."""
    configure_logging()
    configure_sentry()
