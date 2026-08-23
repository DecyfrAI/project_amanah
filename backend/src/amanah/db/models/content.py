"""Collection runs and the one canonical content item every source produces.

`content_items` is the only table that holds source text. Raw and encrypted
columns live here and are excluded from every authenticated-safe projection, so
a reader reaches a permitted excerpt and never the original payload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.db.models.datasets import DatasetImportRun, DatasetPackage
from amanah.db.models.sources import Source, SourceSeedEntry
from amanah.domain.enums import CollectionMode, ContentKind, JobState, ReviewState, SourceStatus

if TYPE_CHECKING:
    from amanah.db.models.analysis import Prediction


class CollectionRun(Base):
    """One bounded execution of one adapter against one source."""

    __tablename__ = "collection_runs"
    __table_args__ = (
        CheckConstraint(
            "window_end IS NULL OR window_start IS NULL OR window_end >= window_start",
            name="window_ordered",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completion_after_start",
        ),
        # A run identifies itself by what it was asked to do, so redelivering the
        # same dispatch cannot start a second run.
        UniqueConstraint("idempotency_key", name="collection_runs_idempotency_key_unique"),
        Index("collection_runs_source_id_started_at_idx", "source_id", text("started_at DESC")),
        Index("collection_runs_status_idx", "status"),
        Index("collection_runs_source_seed_entry_id_idx", "source_seed_entry_id"),
    )

    id: Mapped[UuidPrimaryKey]
    source_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    source_seed_entry_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("source_seed_entries.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[CollectionMode] = mapped_column(enum_column(CollectionMode), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    window_start: Mapped[Timestamp | None]
    window_end: Mapped[Timestamp | None]
    cursor: Mapped[str | None] = mapped_column(Text, doc="Opaque adapter checkpoint.")
    status: Mapped[JobState] = mapped_column(
        enum_column(JobState), nullable=False, server_default="queued"
    )
    counts: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    coverage_warnings: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        doc="Safe, publishable gap descriptions. Never a provider error body.",
    )
    safe_error_code: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[CreatedAt]
    completed_at: Mapped[Timestamp | None]

    source: Mapped[Source] = relationship()
    source_seed_entry: Mapped[SourceSeedEntry | None] = relationship()


class ContentItem(Base):
    """The canonical record every adapter and importer produces.

    Downstream code depends on this shape and never on a provider payload.
    """

    __tablename__ = "content_items"
    __table_args__ = (
        # `spec.md` section 14.6: one row per source item.
        UniqueConstraint(
            "source_id", "source_item_id", name="content_items_source_id_source_item_id_unique"
        ),
        # ...and one row per datapack row, without collapsing the same row ID
        # imported from two different packages.
        Index(
            "content_items_dataset_package_id_dataset_row_id_idx",
            "dataset_package_id",
            "dataset_row_id",
            unique=True,
            postgresql_where=text("dataset_package_id IS NOT NULL"),
        ),
        # Dataset provenance is all-or-nothing: a row cannot claim a package
        # without naming the row it came from, or the reverse.
        CheckConstraint(
            "(dataset_package_id IS NULL) = (dataset_row_id IS NULL)",
            name="dataset_provenance_complete",
        ),
        CheckConstraint(
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'",
            name="country_code_format",
        ),
        CheckConstraint(
            "canonical_url IS NULL OR canonical_url ~ '^https?://'",
            name="canonical_url_scheme",
        ),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_format"),
        # Sort keys for the item list. Each pairs the sort column with `id` so a
        # cursor page cannot drift when two rows share a timestamp.
        Index("content_items_observed_at_id_idx", text("observed_at DESC"), text("id DESC")),
        Index("content_items_published_at_id_idx", text("published_at DESC"), text("id DESC")),
        Index("content_items_source_id_observed_at_idx", "source_id", text("observed_at DESC")),
        Index(
            "content_items_content_kind_observed_at_idx",
            "content_kind",
            text("observed_at DESC"),
        ),
        Index("content_items_collection_run_id_idx", "collection_run_id"),
        Index("content_items_dataset_package_id_idx", "dataset_package_id"),
        Index("content_items_dataset_import_run_id_idx", "dataset_import_run_id"),
        Index("content_items_source_seed_entry_id_idx", "source_seed_entry_id"),
        Index(
            "content_items_country_code_idx",
            "country_code",
            postgresql_where=text("country_code IS NOT NULL"),
        ),
        Index(
            "content_items_submitted_origin_idx",
            "submitted_origin",
            postgresql_where=text("submitted_origin IS NOT NULL"),
        ),
        Index("content_items_canonical_url_idx", "canonical_url"),
    )

    id: Mapped[UuidPrimaryKey]
    source_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    source_item_id: Mapped[str] = mapped_column(
        String(400),
        nullable=False,
        doc=(
            "Opaque provider-side identifier. For a datapack row this is a "
            "deterministic value derived from package, version, and row identity."
        ),
    )
    collection_run_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT")
    )
    source_seed_entry_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("source_seed_entries.id", ondelete="RESTRICT")
    )
    content_kind: Mapped[ContentKind] = mapped_column(enum_column(ContentKind), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)

    dataset_package_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("dataset_packages.id", ondelete="RESTRICT")
    )
    dataset_import_run_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("dataset_import_runs.id", ondelete="RESTRICT")
    )
    dataset_row_id: Mapped[str | None] = mapped_column(String(400))

    title: Mapped[str | None] = mapped_column(Text)
    permitted_excerpt: Mapped[str | None] = mapped_column(
        Text, doc="Licensed or fair-use excerpt only. Never the full source text."
    )
    text_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary, doc="Encrypted permitted original text. Never projected to a reader."
    )
    normalized_text: Mapped[str | None] = mapped_column(
        Text, doc="Model input. Never projected to a reader."
    )
    normalization_version: Mapped[str | None] = mapped_column(String(50))
    raw_object_key: Mapped[str | None] = mapped_column(
        Text, doc="Private storage key. Never projected to a reader."
    )

    publisher_or_container: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[Timestamp | None]
    observed_at: Mapped[Timestamp] = mapped_column(nullable=False)
    language: Mapped[str | None] = mapped_column(String(2))
    country_code: Mapped[str | None] = mapped_column(String(2))
    geographic_scope: Mapped[str | None] = mapped_column(String(50))
    source_status: Mapped[SourceStatus] = mapped_column(
        enum_column(SourceStatus), nullable=False, server_default="available"
    )
    is_fixture: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    submitted_origin: Mapped[UuidColumn | None] = mapped_column(
        doc="The submitting user when this item entered through a URL submission."
    )
    effective_review_state: Mapped[ReviewState] = mapped_column(
        enum_column(ReviewState),
        nullable=False,
        server_default="model_only",
        doc="Projection maintained from appended review events; history is never overwritten.",
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[Timestamp | None] = mapped_column(
        doc="Set only when source terms or a lawful request require deletion."
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Opaque provider payload. Never projected to a reader.",
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    source: Mapped[Source] = relationship(back_populates="content_items")
    dataset_package: Mapped[DatasetPackage | None] = relationship()
    dataset_import_run: Mapped[DatasetImportRun | None] = relationship()
    collection_run: Mapped[CollectionRun | None] = relationship()
    predictions: Mapped[list[Prediction]] = relationship(back_populates="content_item")
