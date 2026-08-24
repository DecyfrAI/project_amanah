"""Request correlation.

Every request carries an identifier that appears in the response headers, in the
error envelope, and in every log line emitted while handling it, so a user-visible
failure can be traced to server logs without exposing anything sensitive.
"""

import re
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-Id"

#: A client-supplied identifier is echoed only when it matches this pattern.
#: Anything else is replaced, which keeps newlines and control characters from a
#: caller out of the log stream.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_request_id: ContextVar[str | None] = ContextVar("amanah_request_id", default=None)
_operation_context: ContextVar[dict[str, str] | None] = ContextVar(
    "amanah_operation_context", default=None
)


def new_request_id() -> str:
    """Generate a fresh request identifier."""
    return f"req_{uuid4().hex}"


def current_request_id() -> str | None:
    """Identifier of the request being handled, or `None` outside a request."""
    return _request_id.get()


def current_operation_context() -> dict[str, str]:
    """Return safe run/job correlation attached to the current execution."""
    return dict(_operation_context.get() or {})


@contextmanager
def bind_operation_context(**values: object) -> Iterator[None]:
    """Temporarily attach run/job/stage identifiers to every emitted log line."""
    safe = {
        key: str(value)
        for key, value in values.items()
        if value is not None and key in {"run_id", "job_id", "stage", "source_key"}
    }
    token = _operation_context.set({**(_operation_context.get() or {}), **safe})
    try:
        yield
    finally:
        _operation_context.reset(token)


def resolve_request_id(candidate: str | None) -> str:
    """Accept a safe client-supplied identifier, otherwise generate one."""
    if candidate is not None and _SAFE_REQUEST_ID.match(candidate):
        return candidate
    return new_request_id()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request identifier and return it on every response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        # Set for the rest of this request and deliberately not reset afterwards.
        # An unhandled exception propagates past this middleware to the handler
        # that converts it into the error envelope, and that handler still needs
        # the identifier; resetting here would strand the failure that most needs
        # correlating. Each request is served in its own task context, so the
        # value cannot leak into another request.
        _request_id.set(request_id)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
