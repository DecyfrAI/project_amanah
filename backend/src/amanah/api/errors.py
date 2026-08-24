"""Conversion of failures into the one safe error envelope.

Exceptions are converted exactly once, here at the HTTP boundary. Handlers below
are the only place that decides a status code, and none of them copies an
exception message, validation input value, or traceback into the response.
"""

import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from amanah.api.schemas.errors import RETRYABLE_ERROR_CODES, ErrorBody, ErrorCode, ErrorEnvelope
from amanah.observability.request_context import (
    REQUEST_ID_HEADER,
    current_request_id,
    new_request_id,
)

logger = logging.getLogger(__name__)

#: Returned for every unauthenticated request regardless of whether the token was
#: absent, malformed, expired, or signed by the wrong key. A caller must not be
#: able to distinguish those cases.
AUTHENTICATION_REQUIRED_MESSAGE = "Authentication is required."

_STATUS_TO_ERROR_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.validation_failed,
    401: ErrorCode.authentication_required,
    403: ErrorCode.permission_denied,
    404: ErrorCode.resource_not_found,
    409: ErrorCode.resource_conflict,
    405: ErrorCode.method_not_allowed,
    429: ErrorCode.rate_limited,
    503: ErrorCode.service_unavailable,
}

ErrorDetails = dict[str, str | int | bool | list[str]]


class ApiError(Exception):
    """A failure that already knows its safe public representation."""

    def __init__(
        self,
        *,
        code: ErrorCode,
        status_code: int,
        message: str,
        details: ErrorDetails | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details: ErrorDetails = details or {}
        self.retry_after_seconds = retry_after_seconds


class AuthenticationRequiredError(ApiError):
    """No valid session was presented."""

    def __init__(self) -> None:
        super().__init__(
            code=ErrorCode.authentication_required,
            status_code=401,
            message=AUTHENTICATION_REQUIRED_MESSAGE,
        )


class PermissionDeniedError(ApiError):
    """The caller is authenticated but not allowed to perform this operation."""

    def __init__(self, message: str = "You do not have access to this resource.") -> None:
        super().__init__(
            code=ErrorCode.permission_denied,
            status_code=403,
            message=message,
        )


class ResourceNotFoundError(ApiError):
    """The resource does not exist, or is not visible to this caller.

    Both cases share one response deliberately: distinguishing them would let a
    caller confirm that a record they cannot read exists.
    """

    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(
            code=ErrorCode.resource_not_found,
            status_code=404,
            message=message,
        )


class RateLimitedError(ApiError):
    """The caller has made too many of this kind of request in the window.

    `rules/api.md` section 14.2 requires `Retry-After` on every `429`, so the
    wait is carried on the error rather than left for the route to remember.
    """

    def __init__(self, *, retry_after_seconds: int, message: str) -> None:
        super().__init__(
            code=ErrorCode.rate_limited,
            status_code=429,
            message=message,
            details={"retry_after_seconds": retry_after_seconds},
            retry_after_seconds=retry_after_seconds,
        )


class ConflictError(ApiError):
    """The request contradicts the current state of the resource.

    Used where a retry cannot succeed until something else changes: a policy
    version that the catalogue has moved past, a review task another reviewer
    already claimed.
    """

    def __init__(self, message: str, *, details: ErrorDetails | None = None) -> None:
        super().__init__(
            code=ErrorCode.resource_conflict,
            status_code=409,
            message=message,
            details=details,
        )


class ServiceUnavailableError(ApiError):
    """A dependency this request needs is not configured or not reachable."""

    def __init__(
        self, message: str = "This service is temporarily unable to answer the request."
    ) -> None:
        super().__init__(
            code=ErrorCode.service_unavailable,
            status_code=503,
            message=message,
        )


def build_error_response(
    *,
    code: ErrorCode,
    status_code: int,
    message: str,
    details: ErrorDetails | None = None,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    """Serialize the safe error envelope."""
    request_id = current_request_id() or new_request_id()
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            retryable=code in RETRYABLE_ERROR_CODES,
            details=details or {},
        )
    )
    # Set here rather than relying on the middleware: an unhandled exception is
    # converted above it, and that response would otherwise carry no header.
    headers = {REQUEST_ID_HEADER: request_id}
    if status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(
        status_code=status_code, content=envelope.model_dump(mode="json"), headers=headers
    )


def _classify_validation_error(errors: list[dict[str, Any]]) -> tuple[ErrorCode, list[str]]:
    """Pick the most specific code and list the offending field paths.

    Only field paths are reported. Submitted values are never echoed back.
    """
    fields = [".".join(str(part) for part in error.get("loc", ())) for error in errors]
    if any(error.get("type") == "extra_forbidden" for error in errors):
        return ErrorCode.unsupported_filter, fields
    if any(field.endswith("sort") for field in fields):
        return ErrorCode.unsupported_sort, fields
    return ErrorCode.validation_failed, fields


async def _handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    # Registered for this type only; the signature is widened by Starlette.
    error = cast(ApiError, exc)
    logger.info(
        "request rejected",
        extra={
            "error_code": error.code.value,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return build_error_response(
        code=error.code,
        status_code=error.status_code,
        message=error.message,
        details=error.details,
        retry_after_seconds=error.retry_after_seconds,
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    code, fields = _classify_validation_error(list(error.errors()))
    logger.info(
        "request validation failed",
        extra={"error_code": code.value, "path": request.url.path, "fields": fields},
    )
    return build_error_response(
        code=code,
        status_code=400,
        message="The request could not be validated.",
        details={"fields": fields},
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    code = _STATUS_TO_ERROR_CODE.get(error.status_code, ErrorCode.internal_error)
    message = (
        AUTHENTICATION_REQUIRED_MESSAGE
        if code is ErrorCode.authentication_required
        else "The request could not be completed."
    )
    logger.info(
        "request failed",
        extra={
            "error_code": code.value,
            "status_code": error.status_code,
            "path": request.url.path,
        },
    )
    return build_error_response(code=code, status_code=error.status_code, message=message)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled server error",
        exc_info=exc,
        extra={"error_code": ErrorCode.internal_error.value, "path": request.url.path},
    )
    return build_error_response(
        code=ErrorCode.internal_error,
        status_code=500,
        message="An unexpected error occurred.",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Install the boundary handlers on the application."""
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
