"""Reviewer claims and append-only decisions (B-S17.4 to B-S17.7).

Three invariants shape this module and each one is enforced by the database
rather than by the order the code happens to run in.

*Claims are leases.* Two reviewers opening the queue at the same moment must not
both work the same task. The claim is a conditional `UPDATE` on the task's
current state, so exactly one of them wins and the other is told to pick another.
An abandoned claim expires and returns to the queue rather than holding it
forever.

*Decisions append.* `review_events` has an append-only trigger from migration
`0002`. A correction adds a row saying what it corrected to; it never edits the
prediction, and a second reviewer disagreeing adds a third row rather than
replacing the second.

*Corrections are quarantined.* `spec.md` FR-DISPUTE-006 and section 15.3 allow an
approved correction into a training-candidate pool only. `is_training_candidate`
is the pool: nothing in this service reads it, no job consumes it, and a model is
never retrained or activated from it. Making it a flag with no consumer is the
point — a pipeline that could pick it up would be the thing the rule forbids.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from amanah.contributions.timeline import ContributionTimeline
from amanah.db.models.analysis import ReviewEvent, ReviewTask
from amanah.db.models.community import ClassificationDispute
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    ContributionEventType,
    ContributionType,
    DisputeStatus,
    ReviewDecision,
    ReviewState,
    ReviewTaskStatus,
)
from amanah.observability.metrics import MetricName, record_metric

logger = logging.getLogger(__name__)

#: How long a claim is held before the task returns to the queue. Long enough to
#: read an item and decide; short enough that a reviewer who closes their laptop
#: does not strand somebody's dispute.
CLAIM_LEASE_MINUTES = 30

#: How an appended decision moves the item's effective review state. The
#: prediction itself is untouched under every one of these.
_DECISION_TO_REVIEW_STATE: dict[ReviewDecision, ReviewState] = {
    ReviewDecision.confirmed: ReviewState.confirmed,
    ReviewDecision.corrected: ReviewState.corrected,
    ReviewDecision.needs_context: ReviewState.needs_context,
    ReviewDecision.rejected: ReviewState.model_only,
}

#: How a decision resolves the disputes attached to the task, and what the
#: disputing user is told. Composed here from controlled vocabulary: a reviewer's
#: private note is never published to the person who complained.
_DECISION_TO_DISPUTE: dict[ReviewDecision, tuple[DisputeStatus, str]] = {
    ReviewDecision.confirmed: (
        DisputeStatus.resolved_upheld,
        "A reviewer looked at this and kept the original classification.",
    ),
    ReviewDecision.corrected: (
        DisputeStatus.resolved_corrected,
        "A reviewer agreed with you and corrected the classification.",
    ),
    ReviewDecision.needs_context: (
        DisputeStatus.resolved_upheld,
        "A reviewer marked this item as needing more context before it can be decided.",
    ),
    ReviewDecision.rejected: (
        DisputeStatus.resolved_upheld,
        "A reviewer set this item back to its unreviewed state.",
    ),
}


class ClaimLostError(RuntimeError):
    """Another reviewer holds this task, or it is no longer open."""


class InvalidDecisionError(ValueError):
    """The decision cannot be appended as asked."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """One reviewer's judgement on one task."""

    decision: ReviewDecision
    note: str | None = None
    corrected_labels: dict[str, Any] | None = None
    is_training_candidate: bool = False


class ReviewService:
    """Owns claims, decisions, and the projections a decision updates."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._timeline = ContributionTimeline(session)

    def claim(self, task_id: UUID, *, reviewer_id: UUID) -> ReviewTask:
        """Take an open task, or refuse because someone else has it.

        The condition covers both cases in one statement: a task that is open, or
        one whose previous claim has expired. Reading first and then updating
        would leave a window in which two reviewers both saw it open.
        """
        now = datetime.now(UTC)
        claimed = self._session.execute(
            update(ReviewTask)
            .where(
                ReviewTask.id == task_id,
                ReviewTask.status.in_((ReviewTaskStatus.open, ReviewTaskStatus.claimed)),
                (ReviewTask.status == ReviewTaskStatus.open)
                | (ReviewTask.claim_expires_at < now)
                | (ReviewTask.assigned_to == reviewer_id),
            )
            .values(
                status=ReviewTaskStatus.claimed,
                assigned_to=reviewer_id,
                claim_expires_at=now + timedelta(minutes=CLAIM_LEASE_MINUTES),
            )
            .returning(ReviewTask.id)
        ).scalar_one_or_none()
        if claimed is None:
            self._session.rollback()
            logger.info("review claim refused", extra={"task_id": str(task_id)})
            raise ClaimLostError
        self._session.commit()
        logger.info(
            "review task claimed",
            extra={"task_id": str(task_id), "reviewer_id": str(reviewer_id)},
        )
        record_metric(MetricName.review_queue, action="claim", outcome="claimed")
        return self._session.get_one(ReviewTask, task_id)

    def decide(self, task_id: UUID, *, reviewer_id: UUID, request: DecisionRequest) -> ReviewEvent:
        """Append one decision and update everything that follows from it.

        Only the reviewer holding the claim may decide, which is what stops a
        second reviewer from settling a task somebody else is mid-way through.
        """
        task = self._session.get(ReviewTask, task_id)
        if task is None:
            raise InvalidDecisionError("This review task was not found.")
        if task.status is not ReviewTaskStatus.claimed or task.assigned_to != reviewer_id:
            raise ClaimLostError
        if (request.decision is ReviewDecision.corrected) != (request.corrected_labels is not None):
            raise InvalidDecisionError(
                "A correction must carry corrected labels, and only a correction may."
            )
        if request.is_training_candidate and request.decision is not ReviewDecision.corrected:
            # `spec.md` FR-DISPUTE-006: only an approved *correction* is a
            # training candidate. Flagging a confirmation would put the model's
            # own output back into its own training pool.
            raise InvalidDecisionError("Only a correction may be marked as a training candidate.")

        event = ReviewEvent(
            review_task_id=task.id,
            reviewer_id=reviewer_id,
            decision=request.decision,
            corrected_labels=request.corrected_labels,
            note=request.note,
            is_training_candidate=request.is_training_candidate,
        )
        self._session.add(event)
        self._session.flush()

        task.status = ReviewTaskStatus.completed
        task.completed_at = datetime.now(UTC)
        task.claim_expires_at = None
        self._session.execute(
            update(ContentItem)
            .where(ContentItem.id == task.content_item_id)
            .values(effective_review_state=_DECISION_TO_REVIEW_STATE[request.decision])
        )
        self._resolve_disputes(task, request.decision)
        self._session.commit()
        logger.info(
            "review decision appended",
            extra={
                "task_id": str(task.id),
                "decision": request.decision.value,
                "is_training_candidate": request.is_training_candidate,
            },
        )
        record_metric(
            MetricName.review_queue,
            action="decision",
            outcome=request.decision.value,
        )
        return event

    def _resolve_disputes(self, task: ReviewTask, decision: ReviewDecision) -> None:
        """Close every dispute the task answered and tell each user (B-S17.6).

        More than one person can dispute the same classification, and one
        decision answers all of them. Each gets their own timeline line, because
        a contribution history is per person.
        """
        status, message = _DECISION_TO_DISPUTE[decision]
        resolved_at = datetime.now(UTC)
        disputes = (
            self._session.execute(
                select(ClassificationDispute).where(
                    ClassificationDispute.review_task_id == task.id,
                    ClassificationDispute.status.in_((DisputeStatus.open, DisputeStatus.in_review)),
                )
            )
            .scalars()
            .all()
        )
        for dispute in disputes:
            dispute.status = status
            dispute.resolution_summary = message
            dispute.resolved_at = resolved_at
            self._timeline.append(
                user_id=dispute.user_id,
                contribution_type=ContributionType.classification_dispute,
                contribution_id=dispute.id,
                event_type=ContributionEventType.resolved,
                public_message=message,
            )

    def release_expired_claims(self, *, now: datetime | None = None) -> int:
        """Return tasks whose reviewer vanished to the open queue."""
        moment = now if now is not None else datetime.now(UTC)
        released = list(
            self._session.execute(
                update(ReviewTask)
                .where(
                    ReviewTask.status == ReviewTaskStatus.claimed,
                    ReviewTask.claim_expires_at < moment,
                )
                .values(status=ReviewTaskStatus.open, assigned_to=None, claim_expires_at=None)
                .returning(ReviewTask.id)
            ).scalars()
        )
        self._session.commit()
        return len(released)
