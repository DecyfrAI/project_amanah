"""Expression-language handles for the authenticated-safe projections.

Repositories read these and never a base table, so a column that is absent from
a projection is unreachable from an endpoint by construction rather than by
review. `tests/db/test_authenticated_projections.py` compares each definition
here against the real view, so the two cannot drift.

Every projection an endpoint reads is declared here. The owner-scoped views
created in `0003` gained handles in Milestone 5, when the contribution, dispute,
review, and discussion endpoints that read them arrived.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
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
    _text_column("sampling_stratum"),
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

authenticated_news = Table(
    "authenticated_news",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("source_name", Text),
    Column("source_homepage", Text),
    Column("title", Text),
    Column("summary", Text),
    Column("url", Text),
    Column("published_at", DateTime(timezone=True)),
    Column("retrieved_at", DateTime(timezone=True)),
    Column("language", Text),
    _text_column("scope"),
    Column("country_code", Text),
    Column("is_fixture", Boolean),
    _text_column("source_status"),
)

authenticated_collection_runs = Table(
    "authenticated_collection_runs",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("source_id", UUID(as_uuid=True)),
    Column("source_key", Text),
    Column("source_name", Text),
    Column("source_seed_entry_id", UUID(as_uuid=True)),
    Column("idempotency_key", Text),
    _text_column("mode"),
    Column("adapter_version", Text),
    Column("window_start", DateTime(timezone=True)),
    Column("window_end", DateTime(timezone=True)),
    _text_column("status"),
    Column("counts", JSONB),
    Column("coverage_warnings", JSONB),
    Column("safe_error_code", Text),
    Column("item_cap", Integer),
    Column("attempt", Integer),
    Column("max_attempts", Integer),
    Column("next_run_at", DateTime(timezone=True)),
    Column("is_dead_lettered", Boolean),
    Column("started_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
)

authenticated_background_jobs = Table(
    "authenticated_background_jobs",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("collection_run_id", UUID(as_uuid=True)),
    _text_column("stage"),
    _text_column("state"),
    Column("attempt", Integer),
    Column("max_attempts", Integer),
    Column("available_at", DateTime(timezone=True)),
    Column("safe_error_code", Text),
    Column("is_dead_lettered", Boolean),
    Column("created_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
)

authenticated_image_examples = Table(
    "authenticated_image_examples",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("title", Text),
    Column("alt_text", Text),
    Column("form_note", Text),
    Column("mime_type", Text),
    Column("byte_size", Integer),
    Column("sha256", Text),
    Column("annotation_hate_types", ARRAY(Text)),
    Column("annotation_severity", SmallInteger),
    Column("annotation_note", Text),
    Column("dataset_provider", Text),
    Column("dataset_name", Text),
    Column("dataset_version", Text),
    Column("dataset_license_id", Text),
    Column("dataset_schema_mapping_version", Text),
    Column("dataset_approval_status", Text),
    Column("dataset_reviewer", Text),
    Column("score", Float),
    Column("narrative_tags", ARRAY(Text)),
    Column("rationale", Text),
    _text_column("relevance"),
    _text_column("stance"),
    _text_column("confidence_tier"),
    Column("predicted_severity", SmallInteger),
    Column("predicted_hate_types", ARRAY(Text)),
    Column("requires_review", Boolean),
    Column("model_name", Text),
    Column("model_version", Text),
    Column("taxonomy_version", Text),
    Column("created_at", DateTime(timezone=True)),
)

authenticated_user_profile = Table(
    "authenticated_user_profile",
    projection_metadata,
    Column("user_id", UUID(as_uuid=True), primary_key=True),
    Column("display_name", Text),
    _text_column("role"),
    _text_column("onboarding_status"),
    Column("content_safety_preferences", JSONB),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)

authenticated_content_submissions = Table(
    "authenticated_content_submissions",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True)),
    Column("submitted_url", Text),
    Column("canonical_url", Text),
    Column("content_item_id", UUID(as_uuid=True)),
    _text_column("status"),
    Column("safe_error_code", Text),
    Column("submitted_at", DateTime(timezone=True)),
    Column("processed_at", DateTime(timezone=True)),
)

authenticated_classification_disputes = Table(
    "authenticated_classification_disputes",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True)),
    Column("content_item_id", UUID(as_uuid=True)),
    Column("prediction_id", UUID(as_uuid=True)),
    Column("reason", Text),
    _text_column("status"),
    Column("resolution_summary", Text),
    Column("created_at", DateTime(timezone=True)),
    Column("resolved_at", DateTime(timezone=True)),
)

authenticated_contribution_events = Table(
    "authenticated_contribution_events",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True)),
    _text_column("contribution_type"),
    Column("contribution_id", UUID(as_uuid=True)),
    _text_column("event_type"),
    Column("public_message", Text),
    Column("created_at", DateTime(timezone=True)),
)

authenticated_prepared_platform_reports = Table(
    "authenticated_prepared_platform_reports",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True)),
    Column("content_item_id", UUID(as_uuid=True)),
    Column("platform", Text),
    Column("platform_policy_id", UUID(as_uuid=True)),
    Column("policy_version", Text),
    Column("evidence_summary", Text),
    Column("suggested_text", Text),
    _text_column("status"),
    Column("submitted_at", DateTime(timezone=True)),
    _text_column("outcome"),
    Column("outcome_note", Text),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    _text_column("recipient_kind"),
    Column("recipient_address", Text),
    Column("draft_subject", Text),
)

authenticated_review_tasks = Table(
    "authenticated_review_tasks",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("content_item_id", UUID(as_uuid=True)),
    Column("prediction_id", UUID(as_uuid=True)),
    _text_column("task_type"),
    Column("reason", Text),
    Column("priority", Integer),
    _text_column("status"),
    Column("assigned_to", UUID(as_uuid=True)),
    Column("claim_expires_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
    Column("title", Text),
    Column("permitted_excerpt", Text),
    Column("canonical_url", Text),
    _text_column("platform"),
    _text_column("relevance"),
    _text_column("stance"),
    Column("hate_types", ARRAY(Text)),
    Column("severity", SmallInteger),
    Column("score", Float),
    _text_column("confidence_tier"),
    Column("model_name", Text),
    Column("model_version", Text),
)

authenticated_review_events = Table(
    "authenticated_review_events",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("review_task_id", UUID(as_uuid=True)),
    Column("reviewer_id", UUID(as_uuid=True)),
    _text_column("decision"),
    Column("corrected_labels", JSONB),
    Column("note", Text),
    Column("is_training_candidate", Boolean),
    Column("created_at", DateTime(timezone=True)),
)

authenticated_snapshot_insights = Table(
    "authenticated_snapshot_insights",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True)),
    Column("author_display_name", Text),
    Column("title", Text),
    Column("claim", Text),
    Column("metric", Text),
    Column("numerator", Integer),
    Column("denominator", Integer),
    Column("window_start", DateTime(timezone=True)),
    Column("window_end", DateTime(timezone=True)),
    Column("figure_label", Text),
    Column("filter_hash", Text),
    Column("explorer_href", Text),
    Column("source_keys", ARRAY(Text)),
    Column("items_observed", Integer),
    Column("items_relevant", Integer),
    Column("created_at", DateTime(timezone=True)),
)

authenticated_dashboard_captures = Table(
    "authenticated_dashboard_captures",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True)),
    Column("alt_text", Text),
    Column("image_source", Text),
    Column("filter_hash", Text),
    Column("explorer_href", Text),
    Column("created_at", DateTime(timezone=True)),
)

authenticated_discussion_posts = Table(
    "authenticated_discussion_posts",
    projection_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("snapshot_insight_id", UUID(as_uuid=True)),
    Column("insight_title", Text),
    Column("user_id", UUID(as_uuid=True)),
    Column("author_display_name", Text),
    Column("body", Text),
    Column("dashboard_capture_id", UUID(as_uuid=True)),
    Column("created_at", DateTime(timezone=True)),
    Column("retracted_at", DateTime(timezone=True)),
)

authenticated_post_reactions = Table(
    "authenticated_post_reactions",
    projection_metadata,
    Column("discussion_post_id", UUID(as_uuid=True), primary_key=True),
    Column("useful_count", BigInteger),
    Column("needs_context_count", BigInteger),
    _text_column("viewer_reaction"),
)

authenticated_discussion_participation = Table(
    "authenticated_discussion_participation",
    projection_metadata,
    Column("user_id", UUID(as_uuid=True), primary_key=True),
    Column("granted_at", DateTime(timezone=True)),
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
        # Queue internals. A checkpoint can carry a provider cursor and a lease
        # owner names a worker; neither belongs in an API response.
        "checkpoint",
        "lease_owner",
        "lease_expires_at",
        "payload",
        "normalized_context",
        "canonical_url_key",
        "headline_key",
    }
)
