"""Curated education resources and frozen research-report snapshots."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.domain.enums import (
    PublicationStatus,
    RedactionMode,
    ResearchReportStatus,
    ResourceCategory,
)


class ResourceEntry(Base):
    """One reviewed external resource.

    Nothing reaches a reader until a person has reviewed it: an entry may only be
    published with a named reviewer and a review date, which is what stops an
    unreviewed AI-drafted description from being served as curation.
    """

    __tablename__ = "resource_entries"
    __table_args__ = (
        UniqueConstraint("url", name="resource_entries_url_unique"),
        CheckConstraint("url LIKE 'https://%'", name="url_https"),
        CheckConstraint(
            "status <> 'published' OR (reviewed_by IS NOT NULL AND last_reviewed_at IS NOT NULL)",
            name="published_requires_review",
        ),
        # The authenticated catalogue read filters on status and orders inside a
        # category, so the index carries both.
        Index(
            "resource_entries_category_title_idx",
            "category",
            "title",
            postgresql_where=text("status = 'published'"),
        ),
        Index("resource_entries_status_idx", "status"),
        Index("resource_entries_country_scope_idx", "country_scope"),
    )

    id: Mapped[UuidPrimaryKey]
    title: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    country_scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="An ISO country code, a multi-country grouping, or 'global'.",
    )
    category: Mapped[ResourceCategory] = mapped_column(
        enum_column(ResourceCategory), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PublicationStatus] = mapped_column(
        enum_column(PublicationStatus), nullable=False, server_default="draft"
    )
    last_reviewed_at: Mapped[Timestamp | None]
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class ResearchReport(Base):
    """A filtered snapshot of what the data said at one moment.

    A snapshot becomes immutable once it is `ready`; regenerating produces a new
    row under a new identifier rather than editing this one. The migration
    enforces that with a trigger, so the guarantee does not depend on callers.
    """

    __tablename__ = "research_reports"
    __table_args__ = (
        CheckConstraint(
            "status <> 'ready' OR completed_at IS NOT NULL",
            name="ready_requires_completion",
        ),
        Index("research_reports_user_id_created_at_idx", "user_id", text("created_at DESC")),
        Index("research_reports_filter_hash_idx", "filter_hash"),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    filter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, doc="The exact validated filters this snapshot was frozen under."
    )
    data_version: Mapped[str] = mapped_column(String(50), nullable=False)
    coverage_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    sections: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    citation_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    methodology_version: Mapped[str] = mapped_column(String(50), nullable=False)
    redaction_mode: Mapped[RedactionMode] = mapped_column(
        enum_column(RedactionMode), nullable=False, server_default="default_redacted"
    )
    status: Mapped[ResearchReportStatus] = mapped_column(
        enum_column(ResearchReportStatus), nullable=False, server_default="pending"
    )
    safe_error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[CreatedAt]
    completed_at: Mapped[Timestamp | None]
