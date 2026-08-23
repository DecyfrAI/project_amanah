"""Expression-language handles for the authenticated-safe projections.

Repositories read these and never a base table, so a column that is absent from
a projection is unreachable from an endpoint by construction rather than by
review. `tests/db/test_authenticated_projections.py` compares each definition
here against the real view, so the two cannot drift.

Only the projections this milestone actually reads are declared. The owner-scoped
views created in `0003` are exercised by the row-level-security tests and gain
handles when the endpoints that read them arrive.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    SmallInteger,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

#: Separate from `Base.metadata` on purpose: these are read handles, and nothing
#: should ever emit `CREATE` for them. The views belong to migration `0003`.
projection_metadata = MetaData(schema="public")


def _text_column(name: str) -> Column[str]:
    """Enum-typed view columns are read as text.

    The database still refuses an unknown label on write; on read the value is
    parsed into its `StrEnum` by the response model, which keeps one validation
    authority instead of two.
    """
    return Column(name, Text)


authenticated_items = Table(
    "authenticated_items",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    _text_column("content_kind"),
    _text_column("platform"),
    _text_column("source_kind"),
    Column("source_name", Text),
    Column("title", Text),
    Column("permitted_excerpt", Text),
    Column("publisher_or_container", Text),
    Column("canonical_url", Text),
    Column("published_at", DateTime(timezone=True)),
    Column("observed_at", DateTime(timezone=True)),
    Column("language", Text),
    Column("country_code", Text),
    Column("geographic_scope", Text),
    _text_column("source_status"),
    Column("is_fixture", Boolean),
    _text_column("review_state"),
    Column("dataset_provider", Text),
    Column("dataset_name", Text),
    Column("dataset_version", Text),
    Column("dataset_license_id", Text),
    Column("dataset_landing_page_url", Text),
    Column("prediction_id", UUID(as_uuid=True)),
    _text_column("relevance"),
    _text_column("stance"),
    Column("hate_types", ARRAY(Text)),
    Column("severity", SmallInteger),
    Column("narrative_tags", ARRAY(Text)),
    Column("score", Float),
    _text_column("confidence_tier"),
    Column("requires_review", Boolean),
    Column("rationale", Text),
    Column("model_name", Text),
    Column("model_version", Text),
    Column("prompt_version", Text),
    Column("taxonomy_version", Text),
    Column("inferred_at", DateTime(timezone=True)),
)

authenticated_metric_buckets = Table(
    "authenticated_metric_buckets",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("metric_key", Text),
    Column("source_id", UUID(as_uuid=True)),
    Column("source_name", Text),
    _text_column("platform"),
    _text_column("interval"),
    Column("bucket_start", DateTime(timezone=True)),
    Column("observed_count", Integer),
    Column("relevant_count", Integer),
    Column("likely_hate_count", Integer),
    Column("reviewed_count", Integer),
    Column("confirmed_count", Integer),
    Column("coverage_score", Float),
    Column("coverage_warnings", JSONB),
    Column("filter_version", Text),
    Column("sampling_disclosure", Text),
)

authenticated_source_status = Table(
    "authenticated_source_status",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("source_key", Text),
    Column("name", Text),
    _text_column("kind"),
    _text_column("platform"),
    Column("purpose", Text),
    Column("policy_url", Text),
    Column("is_enabled", Boolean),
    _text_column("status"),
    Column("last_success_at", DateTime(timezone=True)),
    Column("last_checked_at", DateTime(timezone=True)),
    Column("safe_warning", Text),
)

authenticated_resources = Table(
    "authenticated_resources",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("title", Text),
    Column("organization", Text),
    Column("url", Text),
    Column("country_scope", Text),
    _text_column("category"),
    Column("summary", Text),
    Column("last_reviewed_at", DateTime(timezone=True)),
)

#: Columns that must never appear in any authenticated projection: raw or
#: encrypted source text, private storage keys, opaque provider payloads, and
#: provider-side identifiers that could re-identify an author.
FORBIDDEN_PROJECTION_COLUMNS = frozenset(
    {
        "content_hash",
        "metadata",
        "normalized_text",
        "raw_object_key",
        "source_item_id",
        "submitted_origin",
        "text_ciphertext",
    }
)
