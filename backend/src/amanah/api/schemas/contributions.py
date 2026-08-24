"""Contract for submissions, disputes, and the unified contribution history.

Every model here describes a record its owner may read, and only its owner. The
history row carries exactly what `spec.md` section 9.10 asks a row to show —
type, label, created time, status, last update, destination — and no evidence,
no author identifier, and no reviewer note.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import CursorPageRequest, ResponseMeta
from amanah.canonical.urls import MAXIMUM_URL_LENGTH
from amanah.domain.enums import (
    ContributionEventType,
    ContributionType,
    DisputeStatus,
    SubmissionStatus,
)

#: Longest reason a dispute may carry. Enough to explain the disagreement,
#: bounded so the field cannot be used to store a pasted document.
MAXIMUM_DISPUTE_REASON_LENGTH = 2000


class SubmitUrlRequest(RequestModel):
    """`POST /v1/submissions` body.

    One URL per request (`spec.md` FR-SUBMIT-002). There is no idempotency-key
    header: the natural key is `(user, canonical URL)`, enforced by a partial
    unique index, so a retried submission converges on the record it already
    made.
    """

    url: str = Field(
        min_length=1,
        max_length=MAXIMUM_URL_LENGTH,
        # Anchored and full-string: a partial match would let
        # `javascript:...#https://` through the boundary check.
        pattern=r"^https?://\S+$",
        description="One public HTTP(S) URL. The server normalizes and re-validates it.",
    )


class SubmissionSummary(ResponseModel):
    """One URL submission and where it got to."""

    id: UUID
    submitted_url: str
    canonical_url: str | None
    content_item_id: UUID | None = Field(
        default=None, description="The resulting authenticated-safe item, once there is one."
    )
    status: SubmissionStatus
    safe_error_code: str | None = Field(
        default=None, description="Stable code only; never a provider or retrieval message."
    )
    submitted_at: UtcDatetime
    processed_at: UtcDatetime | None = None


class SubmissionResponse(ResponseModel):
    """`POST /v1/submissions` and `GET /v1/submissions/{id}` payload."""

    submission: SubmissionSummary
    meta: ResponseMeta


class OpenDisputeRequest(RequestModel):
    """`POST /v1/items/{id}/disputes` body."""

    reason: str = Field(
        min_length=1,
        max_length=MAXIMUM_DISPUTE_REASON_LENGTH,
        description="Why the classification looks wrong. Shown to a reviewer, never published.",
    )


class DisputeSummary(ResponseModel):
    """One dispute and its outcome so far."""

    id: UUID
    content_item_id: UUID
    prediction_id: UUID
    reason: str
    status: DisputeStatus
    resolution_summary: str | None = Field(
        default=None, description="User-safe outcome text. Never a reviewer's private note."
    )
    created_at: UtcDatetime
    resolved_at: UtcDatetime | None = None


class DisputeResponse(ResponseModel):
    """`POST /v1/items/{id}/disputes` and `GET /v1/disputes/{id}` payload."""

    dispute: DisputeSummary
    meta: ResponseMeta


class ContributionEventEntry(ResponseModel):
    """One appended line on a contribution's timeline."""

    id: UUID
    contribution_type: ContributionType
    contribution_id: UUID
    event_type: ContributionEventType
    public_message: str
    created_at: UtcDatetime


class ContributionSummary(ResponseModel):
    """One row of Your Contributions (`spec.md` section 9.10)."""

    id: UUID
    contribution_type: ContributionType
    label: str = Field(description="The URL, the dispute reason, or the platform reported to.")
    status: str = Field(description="The record's own status vocabulary; each type has its own.")
    created_at: UtcDatetime
    updated_at: UtcDatetime | None = Field(
        default=None, description="Null while nothing has happened since it was created."
    )
    destination_item_id: UUID | None = Field(
        default=None, description="The item this contribution leads to, when it has one."
    )


class ContributionHistoryQuery(CursorPageRequest):
    """Validated filters for the caller's own history."""

    contribution_type: ContributionType | None = None


class ContributionEventList(ResponseModel):
    """The appended history of one contribution."""

    events: list[ContributionEventEntry]
    meta: ResponseMeta
