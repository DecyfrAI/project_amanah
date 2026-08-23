"""User profiles and the contributions a signed-in person can make.

Every table here is owner-scoped: a user reads their own rows and nobody else's.
Reviewers reach the same records through the review queue, never through an
owner-scoped read. `user_id` is the Supabase `auth.users` identifier; this
service stores product state against it and never mirrors account data.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.db.models.analysis import Prediction, ReviewTask
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    ContributionEventType,
    ContributionType,
    DisputeStatus,
    OnboardingStatus,
    Role,
    SubmissionStatus,
)


class UserProfile(Base):
    """Product state for one authenticated identity.

    The role stored here is the server's record of it. A request is still
    authorized from the verified access token, so a stale row can never grant
    access on its own.
    """

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "display_name IS NULL OR length(display_name) BETWEEN 1 AND 80",
            name="display_name_length",
        ),
        Index("user_profiles_role_idx", "role"),
    )

    user_id: Mapped[UuidColumn] = mapped_column(primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(80))
    role: Mapped[Role] = mapped_column(
        enum_column(Role), nullable=False, server_default="registered_user"
    )
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        enum_column(OnboardingStatus), nullable=False, server_default="not_started"
    )
    content_safety_preferences: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Reveal preferences for redacted text and blurred media.",
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class ContentSubmission(Base):
    """One public URL a user asked the service to analyse."""

    __tablename__ = "content_submissions"
    __table_args__ = (
        # Natural idempotency: the same user resubmitting the same canonical URL
        # links to the existing record instead of starting a second pipeline run.
        Index(
            "content_submissions_user_id_canonical_url_idx",
            "user_id",
            "canonical_url",
            unique=True,
            postgresql_where=text("canonical_url IS NOT NULL"),
        ),
        CheckConstraint("submitted_url ~ '^https?://'", name="submitted_url_scheme"),
        CheckConstraint(
            "status <> 'analyzed' OR content_item_id IS NOT NULL",
            name="analyzed_requires_item",
        ),
        Index("content_submissions_user_id_submitted_at_idx", "user_id", text("submitted_at DESC")),
        Index("content_submissions_content_item_id_idx", "content_item_id"),
        Index("content_submissions_status_idx", "status"),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    submitted_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    content_item_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL")
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        enum_column(SubmissionStatus), nullable=False, server_default="processing"
    )
    safe_error_code: Mapped[str | None] = mapped_column(
        String(100), doc="Stable code only; never a retrieval or provider message."
    )
    submitted_at: Mapped[CreatedAt]
    processed_at: Mapped[Timestamp | None]

    content_item: Mapped[ContentItem | None] = relationship()


class ClassificationDispute(Base):
    """A user's claim that a likely-hate classification is wrong."""

    __tablename__ = "classification_disputes"
    __table_args__ = (
        # `spec.md` section 14.6: one *open* dispute per user and item. A closed
        # dispute does not block a later one on new evidence.
        Index(
            "classification_disputes_user_id_content_item_id_idx",
            "user_id",
            "content_item_id",
            unique=True,
            postgresql_where=text("status IN ('open', 'in_review')"),
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name="resolution_after_creation",
        ),
        CheckConstraint(
            "status NOT IN ('resolved_upheld', 'resolved_corrected') OR resolved_at IS NOT NULL",
            name="resolved_requires_timestamp",
        ),
        Index("classification_disputes_user_id_created_at_idx", "user_id", text("created_at DESC")),
        Index("classification_disputes_content_item_id_idx", "content_item_id"),
        Index("classification_disputes_prediction_id_idx", "prediction_id"),
        Index("classification_disputes_review_task_id_idx", "review_task_id"),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    content_item_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    prediction_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(
        enum_column(DisputeStatus), nullable=False, server_default="open"
    )
    review_task_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("review_tasks.id", ondelete="SET NULL")
    )
    resolution_summary: Mapped[str | None] = mapped_column(
        Text, doc="User-safe outcome text. Never reviewer notes or internal evidence."
    )
    created_at: Mapped[CreatedAt]
    resolved_at: Mapped[Timestamp | None]

    content_item: Mapped[ContentItem] = relationship()
    prediction: Mapped[Prediction] = relationship()
    review_task: Mapped[ReviewTask | None] = relationship()


class ContributionEvent(Base):
    """An appended, user-safe entry on a contribution timeline.

    Rows here are never updated or deleted, so a user's history reads as what
    actually happened rather than as a current-state summary.
    """

    __tablename__ = "contribution_events"
    __table_args__ = (
        # Redelivering the same transition must not append a duplicate line to a
        # user's timeline.
        UniqueConstraint(
            "contribution_id",
            "event_type",
            "public_message",
            name="contribution_events_contribution_event_message_unique",
        ),
        Index("contribution_events_user_id_created_at_idx", "user_id", text("created_at DESC")),
        Index("contribution_events_contribution_id_idx", "contribution_id"),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    contribution_type: Mapped[ContributionType] = mapped_column(
        enum_column(ContributionType), nullable=False
    )
    contribution_id: Mapped[UuidColumn] = mapped_column(
        nullable=False,
        doc=(
            "Identifier of the submission, dispute, or prepared report. Left as a "
            "plain column because it points at one of several owner-scoped tables."
        ),
    )
    event_type: Mapped[ContributionEventType] = mapped_column(
        enum_column(ContributionEventType), nullable=False
    )
    public_message: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Shown to the owning user. Never internal or harmful text."
    )
    created_at: Mapped[CreatedAt]
