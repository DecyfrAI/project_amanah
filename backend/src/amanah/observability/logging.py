"""Structured logging to stdout.

Log records are JSON objects with a fixed core shape. Anything a caller supplies
is passed through `json.dumps`, which escapes newlines and control characters, so
a hostile value cannot forge a second log line.

Never log tokens, secrets, connection strings, URLs containing credentials,
prompts, author identifiers, or raw source content. Log safe identifiers and
error codes instead.
"""

import json
import logging
import sys
from datetime import UTC, datetime

from amanah.observability.request_context import current_operation_context, current_request_id

SERVICE_NAME = "amanah-api"

#: Attributes the standard library sets on every record; anything else on the
#: record was attached deliberately by a caller via `extra=` and is included.
_RESERVED_RECORD_ATTRIBUTES = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | frozenset({"asctime", "message", "taskName"})

_SENSITIVE_KEY_PARTS = frozenset(
    {
        "authorization",
        "content",
        "cookie",
        "credential",
        "password",
        "prompt",
        "secret",
        "text",
        "token",
        "url",
    }
)
_MAX_LOG_VALUE_CHARACTERS = 512


type LogValue = str | int | float | bool | list["LogValue"] | dict[str, "LogValue"] | None


def _safe_log_value(key: str, value: object) -> LogValue:
    """Redact sensitive fields and bound values before serialization."""
    lowered = key.casefold()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, str):
        return value[:_MAX_LOG_VALUE_CHARACTERS]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return [_safe_log_value(key, item) for item in list(value)[:50]]
    if isinstance(value, dict):
        return {
            str(child_key): _safe_log_value(str(child_key), child_value)
            for child_key, child_value in list(value.items())[:50]
        }
    return str(value)[:_MAX_LOG_VALUE_CHARACTERS]


class JsonLogFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, LogValue] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = current_request_id()
        if request_id is not None:
            payload["request_id"] = request_id
        payload.update(current_operation_context())
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRIBUTES:
                payload[key] = _safe_log_value(key, value)
        if record.exc_info is not None:
            # The exception type is safe context; the traceback stays out of the
            # payload so internal paths are never shipped to a log aggregator
            # that may be shared more widely than the host.
            payload["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Send structured logs to stdout at the configured level."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
