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
    ReportRecipientKind,
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
            "official_report_url IS NULL OR official_report_url LIKE 'https://%'",
            name="official_report_url_https",
        ),
        # FR-TOS-010. A channel never carries the other channel's destination, at
        # any status, so the two can never be confused.
        CheckConstraint(
            "recipient_kind <> 'official_form' OR report_email IS NULL",
            name="form_platform_has_report_url",
        ),
        CheckConstraint(
            "recipient_kind <> 'allowlist_email' OR official_report_url IS NULL",
            name="email_platform_has_allowlisted_address",
        ),
        # Completeness is required at publication rather than at insert: a draft
        # exists because a reviewer has not finished it, and only a published
        # entry can be offered to a user.
        CheckConstraint(
            "status <> 'published' "
            "OR (recipient_kind = 'official_form' AND official_report_url IS NOT NULL) "
            "OR (recipient_kind = 'allowlist_email' AND report_email IS NOT NULL)",
            name="published_policy_names_its_destination",
        ),
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
    recipient_kind: Mapped[ReportRecipientKind] = mapped_column(
        enum_column(ReportRecipientKind),
        nullable=False,
        server_default="official_form",
        doc="Whether this platform runs a reporting form or needs an email draft.",
    )
    official_report_url: Mapped[str | None] = mapped_column(
        Text, doc="The platform's own reporting flow. The user submits there themselves."
    )
    report_email: Mapped[str | None] = mapped_column(
        Text,
        doc=(
            "Reviewer-approved allow-listed address for a platform with no reporting "
            "form. Nothing is ever sent to it by this service."
        ),
    )
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
        # FR-TOS-010: an email-style draft carries its allow-listed address and a
        # subject; a form-platform draft carries neither, so a stored row can
        # never imply a recipient the flow did not have.
        CheckConstraint(
            "(recipient_kind = 'allowlist_email') "
            "= (recipient_address IS NOT NULL AND draft_subject IS NOT NULL)",
            name="email_draft_has_recipient",
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
    recipient_kind: Mapped[ReportRecipientKind] = mapped_column(
        enum_column(ReportRecipientKind),
        nullable=False,
        server_default="official_form",
        doc="Copied from the policy at preparation time, so the draft stays self-describing.",
    )
    recipient_address: Mapped[str | None] = mapped_column(
        Text,
        doc=(
            "The allow-listed address an email-style draft is addressed to (FR-TOS-010). "
            "Null for a platform with a reporting form. Never used to send anything."
        ),
    )
    draft_subject: Mapped[str | None] = mapped_column(
        Text, doc="Subject line of an email-style draft. Null for a form platform."
    )
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
