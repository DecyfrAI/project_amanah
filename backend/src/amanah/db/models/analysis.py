"""Model predictions and the append-only human-review history over them.

Predictions and review events are immutable history. A reviewer correction
appends a `review_events` row and updates a projection; it never rewrites what
the model actually produced. The append-only rule is enforced by triggers in the
migration, not only by convention here.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    InferenceStatus,
    Relevance,
    ReviewDecision,
    ReviewTaskStatus,
    ReviewTaskType,
    Stance,
)

#: Severity is a small ordinal band (`spec.md` section 9.5), stored as a
#: `smallint` with a range check rather than an enum so it stays comparable and
#: sortable in SQL.
MINIMUM_SEVERITY = 0
MAXIMUM_SEVERITY = 3


class Prediction(Base):
    """One classification execution over one content item.

    Relevance and stance are separate stages: Muslim-related language is never
    treated as hateful by default, and counterspeech or quotation is its own
    stance rather than a weak form of hate.
    """

    __tablename__ = "predictions"
    __table_args__ = (
        # `spec.md` section 14.6: one execution per item and version triple. A
        # retried inference is therefore idempotent, and re-running a *new*
        # version adds history rather than replacing it.
        UniqueConstraint(
            "content_item_id",
            "model_name",
            "model_version",
            "prompt_version",
            name="predictions_content_item_model_prompt_version_unique",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        CheckConstraint(
            f"severity >= {MINIMUM_SEVERITY} AND severity <= {MAXIMUM_SEVERITY}",
            name="severity_range",
        ),
        # A failed or deferred inference has no labels to stand behind, so it may
        # not claim to have found anti-Muslim rhetoric.
        CheckConstraint(
            "inference_status = 'succeeded' OR stance <> 'likely_anti_muslim'",
            name="unsuccessful_inference_makes_no_claim",
        ),
        Index(
            "predictions_content_item_id_created_at_idx",
            "content_item_id",
            text("created_at DESC"),
        ),
        Index(
            "predictions_requires_review_idx",
            "created_at",
            postgresql_where=text("requires_review"),
        ),
        Index("predictions_confidence_tier_idx", "confidence_tier"),
    )

    id: Mapped[UuidPrimaryKey]
    content_item_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    normalization_version: Mapped[str | None] = mapped_column(String(50))

    relevance: Mapped[Relevance] = mapped_column(enum_column(Relevance), nullable=False)
    stance: Mapped[Stance] = mapped_column(enum_column(Stance), nullable=False)
    hate_types: Mapped[list[HateType]] = mapped_column(
        ARRAY(enum_column(HateType)), nullable=False, server_default=text("'{}'")
    )
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    narrative_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_tier: Mapped[ConfidenceTier] = mapped_column(
        enum_column(ConfidenceTier), nullable=False
    )
    confidence_threshold_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Which versioned threshold set mapped `score` to `confidence_tier`.",
    )
    rationale: Mapped[str | None] = mapped_column(
        Text, doc="Short model explanation. Never a copy of the source text."
    )
    requires_review: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    review_reason: Mapped[str | None] = mapped_column(String(100))
    inference_status: Mapped[InferenceStatus] = mapped_column(
        enum_column(InferenceStatus), nullable=False, server_default="succeeded"
    )
    inferred_at: Mapped[Timestamp | None]
    created_at: Mapped[CreatedAt]

    content_item: Mapped[ContentItem] = relationship(back_populates="predictions")


class ReviewTask(Base):
    """A queued request for a human to look at one prediction."""

    __tablename__ = "review_tasks"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="priority_non_negative"),
        CheckConstraint(
            "status <> 'claimed' OR assigned_to IS NOT NULL",
            name="claimed_requires_assignee",
        ),
        CheckConstraint(
            "status <> 'completed' OR completed_at IS NOT NULL",
            name="completed_requires_timestamp",
        ),
        # One open task per prediction and reason, so a re-queued item joins the
        # existing task instead of flooding the queue.
        Index(
            "review_tasks_prediction_id_task_type_idx",
            "prediction_id",
            "task_type",
            unique=True,
            postgresql_where=text("status IN ('open', 'claimed')"),
        ),
        Index(
            "review_tasks_status_priority_created_at_idx",
            "status",
            text("priority DESC"),
            "created_at",
        ),
        Index("review_tasks_content_item_id_idx", "content_item_id"),
        Index("review_tasks_assigned_to_idx", "assigned_to"),
    )

    id: Mapped[UuidPrimaryKey]
    content_item_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    prediction_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False
    )
    task_type: Mapped[ReviewTaskType] = mapped_column(enum_column(ReviewTaskType), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[ReviewTaskStatus] = mapped_column(
        enum_column(ReviewTaskStatus), nullable=False, server_default="open"
    )
    assigned_to: Mapped[UuidColumn | None]
    claim_expires_at: Mapped[Timestamp | None] = mapped_column(
        doc="Lease expiry, so an abandoned claim returns to the queue."
    )
    created_at: Mapped[CreatedAt]
    completed_at: Mapped[Timestamp | None]

    prediction: Mapped[Prediction] = relationship()
    review_events: Mapped[list[ReviewEvent]] = relationship(back_populates="review_task")


class ReviewEvent(Base):
    """An appended reviewer decision. Rows here are never updated or deleted."""

    __tablename__ = "review_events"
    __table_args__ = (
        # A correction must say what it corrects to; the other decisions must not
        # smuggle labels in through the same column.
        CheckConstraint(
            "(decision = 'corrected') = (corrected_labels IS NOT NULL)",
            name="corrected_labels_match_decision",
        ),
        Index("review_events_review_task_id_created_at_idx", "review_task_id", "created_at"),
        Index("review_events_reviewer_id_idx", "reviewer_id"),
    )

    id: Mapped[UuidPrimaryKey]
    review_task_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("review_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    decision: Mapped[ReviewDecision] = mapped_column(enum_column(ReviewDecision), nullable=False)
    corrected_labels: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(Text)
    is_training_candidate: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("false"),
        doc="Quarantine flag. Nothing trains automatically on an approved correction.",
    )
    created_at: Mapped[CreatedAt]

    review_task: Mapped[ReviewTask] = relationship(back_populates="review_events")
