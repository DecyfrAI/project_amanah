"""Platform-policy catalogue and the reports a user prepares from it.

The product never submits a report to a platform. These tables record what the
user prepared and what they later told us happened; no state here claims that a
platform received anything.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.db.models.analysis import Prediction
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    ConfidenceTier,
    PreparedReportOutcome,
    PreparedReportStatus,
    PublicationStatus,
)


class PlatformPolicy(Base):
    """One reviewed version of one official platform rule."""

    __tablename__ = "platform_policies"
    __table_args__ = (
        # `spec.md` section 14.6.
        UniqueConstraint(
            "platform",
            "policy_key",
            "version",
            name="platform_policies_platform_policy_key_version_unique",
        ),
        CheckConstraint("official_url LIKE 'https://%'", name="official_url_https"),
        CheckConstraint(
            "status <> 'published' OR (reviewed_by IS NOT NULL AND last_reviewed_at IS NOT NULL)",
            name="published_requires_review",
        ),
        Index("platform_policies_platform_status_idx", "platform", "status"),
    )

    id: Mapped[UuidPrimaryKey]
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_at: Mapped[Timestamp | None]
    last_reviewed_at: Mapped[Timestamp | None]
    status: Mapped[PublicationStatus] = mapped_column(
        enum_column(PublicationStatus), nullable=False, server_default="draft"
    )
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class PolicyMatch(Base):
    """A candidate match between one item and one catalogued policy version."""

    __tablename__ = "policy_matches"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        UniqueConstraint(
            "content_item_id",
            "platform_policy_id",
            "model_version",
            name="policy_matches_item_policy_model_version_unique",
        ),
        Index("policy_matches_content_item_id_idx", "content_item_id"),
        Index("policy_matches_platform_policy_id_idx", "platform_policy_id"),
        Index("policy_matches_prediction_id_idx", "prediction_id"),
    )

    id: Mapped[UuidPrimaryKey]
    content_item_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    prediction_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False
    )
    platform_policy_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("platform_policies.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_tier: Mapped[ConfidenceTier] = mapped_column(
        enum_column(ConfidenceTier), nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[CreatedAt]

    content_item: Mapped[ContentItem] = relationship()
    prediction: Mapped[Prediction] = relationship()
    platform_policy: Mapped[PlatformPolicy] = relationship()


class PreparedPlatformReport(Base):
    """Wording and evidence a user prepared, to submit themselves."""

    __tablename__ = "prepared_platform_reports"
    __table_args__ = (
        # Anti-brigading: one prepared report per user, item, and platform.
        UniqueConstraint(
            "user_id",
            "content_item_id",
            "platform",
            name="prepared_platform_reports_user_item_platform_unique",
        ),
        CheckConstraint(
            "status <> 'submitted' OR submitted_at IS NOT NULL",
            name="submitted_requires_timestamp",
        ),
        # An outcome is something the user reports back after submitting; a
        # merely prepared report has none.
        CheckConstraint(
            "outcome IS NULL OR status <> 'prepared'",
            name="outcome_requires_submission",
        ),
        Index(
            "prepared_platform_reports_user_id_created_at_idx", "user_id", text("created_at DESC")
        ),
        Index("prepared_platform_reports_content_item_id_idx", "content_item_id"),
        Index("prepared_platform_reports_platform_policy_id_idx", "platform_policy_id"),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    content_item_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_policy_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("platform_policies.id", ondelete="RESTRICT"), nullable=False
    )
    policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Frozen at preparation time, so a later catalogue update cannot rewrite history.",
    )
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PreparedReportStatus] = mapped_column(
        enum_column(PreparedReportStatus), nullable=False, server_default="prepared"
    )
    submitted_at: Mapped[Timestamp | None] = mapped_column(
        doc="When the *user* said they submitted it. Never a platform acknowledgement."
    )
    outcome: Mapped[PreparedReportOutcome | None] = mapped_column(
        enum_column(PreparedReportOutcome)
    )
    outcome_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    content_item: Mapped[ContentItem] = relationship()
    platform_policy: Mapped[PlatformPolicy] = relationship()
