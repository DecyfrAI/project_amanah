"""The single safe error envelope returned by every failing API operation.

`details` carries only safe, actionable fields. Provider response bodies, stack
traces, raw SQL, internal paths, dependency versions, secrets, and harmful source
content never reach this model.
"""

from enum import StrEnum

from pydantic import Field

from amanah.api.schemas.base import ResponseModel


class ErrorCode(StrEnum):
    """Stable machine-readable error codes.

    Codes are part of the `/v1` contract: new codes may be added, existing codes
    are never renamed.
    """

    validation_failed = "VALIDATION_FAILED"
    unsupported_filter = "UNSUPPORTED_FILTER"
    unsupported_sort = "UNSUPPORTED_SORT"
    authentication_required = "AUTHENTICATION_REQUIRED"
    permission_denied = "PERMISSION_DENIED"
    resource_not_found = "RESOURCE_NOT_FOUND"
    method_not_allowed = "METHOD_NOT_ALLOWED"
    rate_limited = "RATE_LIMITED"
    service_unavailable = "SERVICE_UNAVAILABLE"
    internal_error = "INTERNAL_ERROR"


#: Codes whose failure may succeed on a later identical request.
RETRYABLE_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {ErrorCode.rate_limited, ErrorCode.service_unavailable}
)


class ErrorBody(ResponseModel):
    """Machine-readable failure description."""

    code: ErrorCode
    message: str = Field(min_length=1, description="Safe, actionable, user-presentable text.")
    request_id: str = Field(min_length=1, description="Correlates the failure with server logs.")
    retryable: bool
    details: dict[str, str | int | bool | list[str]] = Field(default_factory=dict)


class ErrorEnvelope(ResponseModel):
    """Top-level error response body."""

    error: ErrorBody
