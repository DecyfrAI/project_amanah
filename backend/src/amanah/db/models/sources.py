"""Configured sources and the approved seed entries that may run against them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.domain.enums import (
    ApprovalStatus,
    ConnectorStatus,
    PublicPlatform,
    RetentionPolicy,
    SamplingStratum,
    SeedEntryKind,
    SourceKind,
)

if TYPE_CHECKING:
    from amanah.db.models.content import ContentItem

#: The single controlled row every open-datapack record points at, so that its
#: public source and platform display as `N/A` while dataset lineage is kept in
#: its own columns. `spec.md` section 14.6 requires exactly one such record.
OPEN_DATAPACK_SOURCE_KEY = "open_datapack"

#: Public display value stored on the controlled row above.
NOT_APPLICABLE_SOURCE_NAME = "N/A"


class Source(Base):
    """A configured origin of content: a news feed, a platform, or a datapack.

    `source_key` is the stable identifier configuration refers to; `name` is what
    a reader sees. They are separate so renaming the display label never breaks a
    stored reference.
    """

    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("source_key", name="sources_source_key_unique"),
        # Exactly one controlled open-datapack row may exist, which is what makes
        # `N/A` a single well-known source rather than a magic string per import.
        Index(
            "sources_open_datapack_singleton_idx",
            "kind",
            unique=True,
            postgresql_where=text("kind = 'open_datapack'"),
        ),
    )

    id: Mapped[UuidPrimaryKey]
    source_key: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(enum_column(SourceKind), nullable=False)
    platform: Mapped[PublicPlatform] = mapped_column(
        enum_column(PublicPlatform),
        nullable=False,
        doc="Platform shown to readers; open-datapack rows use `not_applicable`.",
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_url: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    status: Mapped[ConnectorStatus] = mapped_column(
        enum_column(ConnectorStatus),
        nullable=False,
        server_default="not_configured",
    )
    purpose: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Why this source is collected, in plain language."
    )
    config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_policy: Mapped[RetentionPolicy] = mapped_column(
        enum_column(RetentionPolicy), nullable=False
    )
    last_success_at: Mapped[Timestamp | None]
    last_checked_at: Mapped[Timestamp | None]
    safe_warning: Mapped[str | None] = mapped_column(
        Text, doc="Publishable coverage warning. Never a provider error body."
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    seed_entries: Mapped[list[SourceSeedEntry]] = relationship(back_populates="source")
    content_items: Mapped[list[ContentItem]] = relationship(back_populates="source")


class SourceSeedEntry(Base):
    """One reviewed, approved seed or query a source may collect from.

    The Markdown seed registry is human reference input only. A row lands here
    when someone reviews an entry and copies it into versioned configuration,
    which is why `registry_key` plus `config_version` is the identity: a heading
    position in a document never is.
    """

    __tablename__ = "source_seed_entries"
    __table_args__ = (
        UniqueConstraint(
            "registry_key",
            "config_version",
            name="source_seed_entries_registry_key_config_version_unique",
        ),
        CheckConstraint("item_cap > 0", name="item_cap_positive"),
        # English-only is the MVP language gate; widening it is a configuration
        # and evaluation decision, not an accident of an unchecked column.
        CheckConstraint("language ~ '^[a-z]{2}$'", name="language_format"),
        Index("source_seed_entries_source_id_idx", "source_id"),
        Index(
            "source_seed_entries_source_id_sampling_stratum_idx",
            "source_id",
            "sampling_stratum",
            postgresql_where=text("approval_status = 'approved'"),
        ),
    )

    id: Mapped[UuidPrimaryKey]
    registry_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    entry_kind: Mapped[SeedEntryKind] = mapped_column(enum_column(SeedEntryKind), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider_reference: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Opaque provider-side identifier or query string."
    )
    query_family: Mapped[str] = mapped_column(String(100), nullable=False)
    query_purpose: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Why this entry is sampled. Inclusion is sampling relevance, not a hate label.",
    )
    sampling_stratum: Mapped[SamplingStratum] = mapped_column(
        enum_column(SamplingStratum), nullable=False
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    country_scope: Mapped[str | None] = mapped_column(String(50))
    item_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_column(ApprovalStatus), nullable=False, server_default="pending"
    )
    approved_by: Mapped[str | None] = mapped_column(Text)
    config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    last_reviewed_at: Mapped[Timestamp | None]
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    source: Mapped[Source] = relationship(back_populates="seed_entries")
