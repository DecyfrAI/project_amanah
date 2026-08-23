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
from typing import Any

from amanah.observability.request_context import current_request_id

SERVICE_NAME = "amanah-api"

#: Attributes the standard library sets on every record; anything else on the
#: record was attached deliberately by a caller via `extra=` and is included.
_RESERVED_RECORD_ATTRIBUTES = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | frozenset({"asctime", "message", "taskName"})


class JsonLogFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = current_request_id()
        if request_id is not None:
            payload["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRIBUTES:
                payload[key] = value
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
