"""Shared conventions for every `/v1` request and response model.

Contract rules enforced here rather than repeated per model:

* JSON field names are `snake_case`.
* Every timestamp is timezone-aware and serialized as UTC ISO-8601.
* Requests reject unknown fields so an unsupported filter is a client error
  instead of a silently broadened query.
* Responses keep explicit `null` for "known to be absent" rather than omitting
  the field. This is a deliberate deviation from `rules/api.md` section 6.2:
  the dashboard must distinguish "no value" from "not collected", and the
  frontend validates responses against the same models.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def _require_utc(value: datetime) -> datetime:
    """Reject naive timestamps and normalize aware timestamps to UTC."""
    if value.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_require_utc)]


class ResponseModel(BaseModel):
    """Base for models the API returns.

    Frozen so a response object cannot be mutated after construction, and
    `extra="forbid"` so a field added by mistake fails loudly in tests.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class RequestModel(BaseModel):
    """Base for models parsed from client input.

    `extra="forbid"` turns an unknown query parameter or body field into a
    validation error, which the error handler maps to `400 VALIDATION_FAILED`.
    """

    model_config = ConfigDict(extra="forbid")
