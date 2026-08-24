"""Contract for the reviewer queue and its append-only decisions (B-S17.4).

A queue entry carries the item and the prediction a reviewer has to judge and
deliberately not the identity of whoever disputed it. A decision is appended; the
response is the event that was written, never a rewritten prediction.
"""

from __future__ import annotations

from typing import Any, Self
from uuid import UUID

from pydantic import Field, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import CursorPageRequest, ResponseMeta
from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    PublicPlatform,
    Relevance,
    ReviewDecision,
    ReviewTaskStatus,
    ReviewTaskType,
    Severity,
    Stance,
)

#: Longest note a reviewer may attach. It is internal: the disputing user sees a
#: composed resolution summary, never this text.
MAXIMUM_REVIEWER_NOTE_LENGTH = 2000


class ReviewTaskSummary(ResponseModel):
    """One item waiting for a human decision."""

    id: UUID
    content_item_id: UUID
    prediction_id: UUID
    task_type: ReviewTaskType
    reason: str
    priority: int = Field(ge=0)
    status: ReviewTaskStatus
    assigned_to: UUID | None = None
    claim_expires_at: UtcDatetime | None = None
    created_at: UtcDatetime
    completed_at: UtcDatetime | None = None

    title: str | None = None
    permitted_excerpt: str | None = None
    canonical_url: str | None = None
    platform: PublicPlatform

    relevance: Relevance
    stance: Stance
    hate_types: list[HateType]
    severity: int = Field(ge=int(Severity.none), le=int(Severity.high))
    score: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    model_name: str
    model_version: str


class ReviewQueueQuery(CursorPageRequest):
    """Validated filters for the review queue."""

    status: ReviewTaskStatus | None = None
    task_type: ReviewTaskType | None = None


class ReviewTaskResponse(ResponseModel):
    """One task with every decision appended to it so far."""

    task: ReviewTaskSummary
    decisions: list[ReviewDecisionEntry]
    meta: ResponseMeta


class AppendDecisionRequest(RequestModel):
    """`POST /v1/review/tasks/{id}/decisions` body."""

    decision: ReviewDecision
    note: str | None = Field(default=None, max_length=MAXIMUM_REVIEWER_NOTE_LENGTH)
    corrected_labels: dict[str, Any] | None = Field(
        default=None,
        description="Required for a correction, forbidden otherwise. Never edits the prediction.",
    )
    is_training_candidate: bool = Field(
        default=False,
        description=(
            "Quarantine flag only. A flagged correction enters a governed pool; "
            "nothing retrains or activates a model from it."
        ),
    )

    @model_validator(mode="after")
    def _check_correction(self) -> Self:
        if (self.decision is ReviewDecision.corrected) != (self.corrected_labels is not None):
            raise ValueError("a correction must carry corrected labels, and only a correction may")
        if self.is_training_candidate and self.decision is not ReviewDecision.corrected:
            raise ValueError("only a correction may be marked as a training candidate")
        return self


class ReviewDecisionEntry(ResponseModel):
    """One appended decision. Rows behind this are never updated or deleted."""

    id: UUID
    review_task_id: UUID
    reviewer_id: UUID
    decision: ReviewDecision
    corrected_labels: dict[str, Any] | None = None
    note: str | None = None
    is_training_candidate: bool
    created_at: UtcDatetime


class ReviewDecisionResponse(ResponseModel):
    """`POST /v1/review/tasks/{id}/decisions` payload."""

    decision: ReviewDecisionEntry
    meta: ResponseMeta


ReviewTaskResponse.model_rebuild()
