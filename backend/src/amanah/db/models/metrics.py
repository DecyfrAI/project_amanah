"""Deterministic metric buckets, news association, and cached narrative output.

Every number the dashboard shows is computed here in code or SQL. Gemini may
explain a stored bundle of these facts; it never produces or recalculates one.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    MetricInterval,
    RelationBasis,
    RelationReviewState,
    SamplingStratum,
    ValidationStatus,
)

#: `spec.md` section 9.5. The one rate the dashboard leads with, always reported
#: as a rate *in the monitored sample* and never as public sentiment.
LIKELY_ANTI_MUSLIM_RATE_KEY = "likely_anti_muslim_rate"


class MetricBucket(Base):
    """One deterministic aggregate over one source, interval, and window.

    Counts are stored rather than a rate. A rate is derived at read time from a
    numerator and a denominator that travel with it, and a bucket that was never
    collected is simply absent — a gap, never a stored zero.
    """

    __tablename__ = "metric_buckets"
    __table_args__ = (
        # `spec.md` section 14.6. `filter_version` is part of the identity so
        # recomputing under a new filter definition adds a bucket instead of
        # silently rewriting history, and `sampling_stratum` is part of it so an
        # enriched sample can never be aggregated into the same row as ordinary
        # monitoring.
        UniqueConstraint(
            "metric_key",
            "source_id",
            "sampling_stratum",
            "interval",
            "bucket_start",
            "filter_version",
            name="metric_buckets_key_source_stratum_interval_bucket_filter_unique",
        ),
        CheckConstraint(
            "observed_count >= 0 AND relevant_count >= 0 AND likely_hate_count >= 0 "
            "AND reviewed_count >= 0 AND confirmed_count >= 0",
            name="counts_non_negative",
        ),
        # The counts nest, so a stored bucket can never produce a rate above one.
        CheckConstraint(
            "relevant_count <= observed_count "
            "AND likely_hate_count <= relevant_count "
            "AND confirmed_count <= reviewed_count "
            "AND reviewed_count <= observed_count",
            name="counts_nested",
        ),
        CheckConstraint(
            "coverage_score IS NULL OR (coverage_score >= 0 AND coverage_score <= 1)",
            name="coverage_score_range",
        ),
        Index(
            "metric_buckets_metric_key_interval_bucket_start_idx",
            "metric_key",
            "interval",
            text("bucket_start DESC"),
        ),
        Index("metric_buckets_source_id_idx", "source_id"),
    )

    id: Mapped[UuidPrimaryKey]
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    sampling_stratum: Mapped[SamplingStratum] = mapped_column(
        enum_column(SamplingStratum),
        nullable=False,
        server_default="ordinary_monitoring",
        doc=(
            "Why the items in this bucket were sampled. Part of the bucket's identity "
            "so an enriched seed sample and ordinary monitoring can never be summed "
            "into one figure and published as prevalence."
        ),
    )
    interval: Mapped[MetricInterval] = mapped_column(enum_column(MetricInterval), nullable=False)
    bucket_start: Mapped[CreatedAt]
    observed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    relevant_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    likely_hate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reviewed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    confirmed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    coverage_score: Mapped[float | None] = mapped_column(Float)
    coverage_warnings: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    filter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    sampling_disclosure: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Plain-language statement of what this sample does and does not represent.",
    )
    created_at: Mapped[CreatedAt]


class NewsEventLink(Base):
    """A proposed association between a news item and a metric movement.

    Association is not causation. The basis and the human review state are stored
    with the score so a reader can judge the claim rather than inherit it.
    """

    __tablename__ = "news_event_links"
    __table_args__ = (
        CheckConstraint(
            "relation_score >= 0 AND relation_score <= 1",
            name="relation_score_range",
        ),
        UniqueConstraint(
            "content_item_id",
            "related_metric_key",
            name="news_event_links_content_item_id_related_metric_key_unique",
        ),
        Index("news_event_links_related_metric_key_idx", "related_metric_key"),
    )

    id: Mapped[UuidPrimaryKey]
    content_item_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    related_metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    relation_score: Mapped[float] = mapped_column(Float, nullable=False)
    relation_basis: Mapped[RelationBasis] = mapped_column(
        enum_column(RelationBasis), nullable=False
    )
    review_state: Mapped[RelationReviewState] = mapped_column(
        enum_column(RelationReviewState), nullable=False, server_default="unreviewed"
    )
    created_at: Mapped[CreatedAt]

    content_item: Mapped[ContentItem] = relationship()


class InsightSnapshot(Base):
    """A cached narrative summary over an immutable bundle of stored facts."""

    __tablename__ = "insight_snapshots"
    __table_args__ = (
        # The cache key is the filter, the data version, and every version that
        # could change the wording, so a model or prompt change cannot serve a
        # stale narrative.
        UniqueConstraint(
            "filter_hash",
            "data_version",
            "model_name",
            "prompt_version",
            name="insight_snapshots_filter_data_model_prompt_unique",
        ),
        Index("insight_snapshots_generated_at_idx", text("generated_at DESC")),
    )

    id: Mapped[UuidPrimaryKey]
    filter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc=(
            "Digest of the exact fact bundle this narrative was generated from. "
            "New data produces a new digest, so a re-run after collection is a cache "
            "miss rather than a stale summary served over fresh figures."
        ),
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_fact_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    citation_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    validation_status: Mapped[ValidationStatus] = mapped_column(
        enum_column(ValidationStatus), nullable=False, server_default="pending"
    )
    generated_at: Mapped[CreatedAt]
