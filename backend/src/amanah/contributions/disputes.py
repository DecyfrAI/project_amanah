"""Classification disputes and the review tasks they raise (B-S17.1 to B-S17.3).

A dispute never changes a prediction. `spec.md` FR-DISPUTE-004 makes review
history append-only, and the model's output is a record of what the model
actually said — rewriting it would destroy the only evidence that the correction
was needed. What a dispute does is create a review task and move the item's
*effective* review state to `disputed`, which is a projection and not the
prediction itself.

`spec.md` section 14.6 allows one **open** dispute per user and item, enforced by
a partial unique index. A resolved dispute does not block a later one: new
evidence about the same item is a new dispute, not an amendment to a closed one.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.contributions.rate_limit import DISPUTE_LIMIT, enforce
from amanah.contributions.timeline import ContributionTimeline
from amanah.db.models.analysis import Prediction, ReviewTask
from amanah.db.models.community import ClassificationDispute
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    ContributionEventType,
    ContributionType,
    DisputeStatus,
    ReviewState,
    ReviewTaskStatus,
    ReviewTaskType,
)

logger = logging.getLogger(__name__)

#: Disputes jump the queue ahead of routine low-confidence review: a person is
#: waiting on the answer, which nothing else in the queue can say.
DISPUTE_PRIORITY = 100

#: States in which a dispute is still the user's open question.
OPEN_STATUSES = (DisputeStatus.open, DisputeStatus.in_review)

_CREATED_MESSAGE = "We received your dispute and sent it to a reviewer."


class DisputeRejectedError(ValueError):
    """The dispute cannot be opened as asked.

    Carries a stable safe code so the route can pick a status and a message
    without re-deriving why.
    """

    def __init__(self, safe_error_code: str, message: str) -> None:
        super().__init__(message)
        self.safe_error_code = safe_error_code
        self.message = message


@dataclass(frozen=True, slots=True)
class DisputeResult:
    """One dispute and whether this request is what opened it."""

    dispute: ClassificationDispute
    is_new: bool


class DisputeService:
    """Owns the creation of disputes and the review tasks behind them."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._timeline = ContributionTimeline(session)

    def open(self, *, user_id: UUID, content_item_id: UUID, reason: str) -> DisputeResult:
        """Open a dispute, or return the open one this user already has.

        B-S17.2: an idempotent retry returns the existing dispute rather than
        failing, because a client that lost the response has no way to tell a
        duplicate from a first attempt.
        """
        existing = self._find_open(user_id=user_id, content_item_id=content_item_id)
        if existing is not None:
            logger.info(
                "dispute absorbed a duplicate delivery",
                extra={"dispute_id": str(existing.id)},
            )
            return DisputeResult(dispute=existing, is_new=False)

        prediction_id = self._current_prediction(content_item_id)
        if prediction_id is None:
            raise DisputeRejectedError(
                "item_has_no_classification",
                "This item has no classification to dispute yet.",
            )

        enforce(
            self._session,
            DISPUTE_LIMIT,
            user_id=user_id,
            owner_column=ClassificationDispute.user_id,
            created_column=ClassificationDispute.created_at,
        )

        task = self._open_review_task(content_item_id=content_item_id, prediction_id=prediction_id)
        dispute = ClassificationDispute(
            user_id=user_id,
            content_item_id=content_item_id,
            prediction_id=prediction_id,
            reason=reason,
            status=DisputeStatus.open,
            review_task_id=task.id,
        )
        self._session.add(dispute)
        self._session.flush()

        # The projection, never the prediction. `spec.md` FR-DISPUTE-004.
        self._session.execute(
            update(ContentItem)
            .where(ContentItem.id == content_item_id)
            .values(effective_review_state=ReviewState.disputed)
        )
        self._timeline.append(
            user_id=user_id,
            contribution_type=ContributionType.classification_dispute,
            contribution_id=dispute.id,
            event_type=ContributionEventType.created,
            public_message=_CREATED_MESSAGE,
        )
        self._session.commit()
        logger.info(
            "dispute opened",
            extra={"dispute_id": str(dispute.id), "review_task_id": str(task.id)},
        )
        return DisputeResult(dispute=dispute, is_new=True)

    def _find_open(self, *, user_id: UUID, content_item_id: UUID) -> ClassificationDispute | None:
        return self._session.execute(
            select(ClassificationDispute).where(
                ClassificationDispute.user_id == user_id,
                ClassificationDispute.content_item_id == content_item_id,
                ClassificationDispute.status.in_(OPEN_STATUSES),
            )
        ).scalar_one_or_none()

    def _current_prediction(self, content_item_id: UUID) -> UUID | None:
        """The newest successful prediction, which is what a reader was shown."""
        return self._session.execute(
            select(Prediction.id)
            .where(
                Prediction.content_item_id == content_item_id,
                Prediction.inference_status == "succeeded",
            )
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _open_review_task(self, *, content_item_id: UUID, prediction_id: UUID) -> ReviewTask:
        """Join the open dispute task for this prediction, or create it.

        Two people disputing the same classification is one question for a
        reviewer, not two. The partial unique index on `(prediction_id,
        task_type)` for open tasks is what makes the join a guarantee rather than
        a race.
        """
        created = self._session.execute(
            insert(ReviewTask)
            .values(
                content_item_id=content_item_id,
                prediction_id=prediction_id,
                task_type=ReviewTaskType.dispute,
                reason="A signed-in user disputed this classification.",
                priority=DISPUTE_PRIORITY,
                status=ReviewTaskStatus.open,
            )
            .on_conflict_do_nothing(
                index_elements=[ReviewTask.prediction_id, ReviewTask.task_type],
                # The unique index is partial, so the inference has to name the
                # same predicate or Postgres cannot match it.
                index_where=text("status IN ('open', 'claimed')"),
            )
            .returning(ReviewTask.id)
        ).scalar_one_or_none()
        if created is not None:
            return self._session.get_one(ReviewTask, created)

        return self._session.execute(
            select(ReviewTask).where(
                ReviewTask.prediction_id == prediction_id,
                ReviewTask.task_type == ReviewTaskType.dispute,
                ReviewTask.status.in_((ReviewTaskStatus.open, ReviewTaskStatus.claimed)),
            )
        ).scalar_one()
