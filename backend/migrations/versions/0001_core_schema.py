"""Core relational schema: sources, content, analysis, contributions, reporting.

Creates the controlled enum types, then every product table with its documented
unique, check, and foreign-key constraints and only the indexes a planned query
needs. Access control is deliberately *not* here: append-only enforcement is
`0002`, and the authenticated-safe projections and row-level-security boundary
are `0003`. Each migration does one logical thing (`rules/database.md`).

Revision ID: 0001_core_schema
Revises: nothing; this is the first migration
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from amanah.db.enums import ENUM_TYPES

revision: str = "0001_core_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_type(name: str) -> postgresql.ENUM:
    """Reference an enum type this migration already created.

    `create_type=False` matters: without it every column that mentions the type
    would emit its own `CREATE TYPE` and the second one would fail.
    """
    return postgresql.ENUM(name=name, create_type=False, schema="public")


def _create_enum_types() -> None:
    """Create one Postgres enum per controlled vocabulary.

    The labels come from `amanah.domain.enums` through `ENUM_TYPES`, so the
    database and the published `/v1` contract cannot describe different value
    sets. Label text is generated from Python enum members and never from input.
    """
    for python_enum, type_name in ENUM_TYPES:
        labels = ", ".join(f"'{member.value}'" for member in python_enum)
        op.execute(f"CREATE TYPE public.{type_name} AS ENUM ({labels})")


def _drop_enum_types() -> None:
    for _python_enum, type_name in reversed(ENUM_TYPES):
        op.execute(f"DROP TYPE IF EXISTS public.{type_name}")


def upgrade() -> None:
    _create_enum_types()
    op.create_table(
        "contribution_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("contribution_type", enum_type("contribution_type"), nullable=False),
        sa.Column("contribution_id", sa.UUID(), nullable=False),
        sa.Column("event_type", enum_type("contribution_event_type"), nullable=False),
        sa.Column("public_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("contribution_events_pkey")),
        sa.UniqueConstraint(
            "contribution_id",
            "event_type",
            "public_message",
            name="contribution_events_contribution_event_message_unique",
        ),
        schema="public",
    )
    op.create_index(
        "contribution_events_contribution_id_idx",
        "contribution_events",
        ["contribution_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "contribution_events_user_id_created_at_idx",
        "contribution_events",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_table(
        "dataset_packages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=200), nullable=False),
        sa.Column("landing_page_url", sa.Text(), nullable=False),
        sa.Column("license_id", sa.String(length=100), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("permitted_uses", sa.Text(), nullable=False),
        sa.Column(
            "approval_status",
            enum_type("approval_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_mapping_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "approval_status <> 'approved' OR approved_by IS NOT NULL",
            name=op.f("dataset_packages_approved_by_required_check"),
        ),
        sa.CheckConstraint(
            "file_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("dataset_packages_file_sha256_format_check")
        ),
        sa.CheckConstraint(
            "landing_page_url LIKE 'https://%%'",
            name=op.f("dataset_packages_landing_page_url_https_check"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("dataset_packages_pkey")),
        sa.UniqueConstraint(
            "provider", "name", "version", name="dataset_packages_provider_name_version_unique"
        ),
        schema="public",
    )
    op.create_index(
        "dataset_packages_approval_status_idx",
        "dataset_packages",
        ["approval_status"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "insight_snapshots",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("filter_hash", sa.String(length=64), nullable=False),
        sa.Column("data_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column(
            "input_fact_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "citation_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "validation_status",
            enum_type("validation_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("insight_snapshots_pkey")),
        sa.UniqueConstraint(
            "filter_hash",
            "data_version",
            "model_name",
            "prompt_version",
            name="insight_snapshots_filter_data_model_prompt_unique",
        ),
        schema="public",
    )
    op.create_index(
        "insight_snapshots_generated_at_idx",
        "insight_snapshots",
        [sa.literal_column("generated_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_table(
        "platform_policies",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("policy_key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", enum_type("publication_status"), server_default="draft", nullable=False
        ),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "official_url LIKE 'https://%%'",
            name=op.f("platform_policies_official_url_https_check"),
        ),
        sa.CheckConstraint(
            "status <> 'published' OR (reviewed_by IS NOT NULL AND last_reviewed_at IS NOT NULL)",
            name=op.f("platform_policies_published_requires_review_check"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("platform_policies_pkey")),
        sa.UniqueConstraint(
            "platform",
            "policy_key",
            "version",
            name="platform_policies_platform_policy_key_version_unique",
        ),
        schema="public",
    )
    op.create_index(
        "platform_policies_platform_status_idx",
        "platform_policies",
        ["platform", "status"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "research_reports",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("filter_hash", sa.String(length=64), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_version", sa.String(length=50), nullable=False),
        sa.Column(
            "coverage_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "sections",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "citation_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("methodology_version", sa.String(length=50), nullable=False),
        sa.Column(
            "redaction_mode",
            enum_type("redaction_mode"),
            server_default="default_redacted",
            nullable=False,
        ),
        sa.Column(
            "status", enum_type("research_report_status"), server_default="pending", nullable=False
        ),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status <> 'ready' OR completed_at IS NOT NULL",
            name=op.f("research_reports_ready_requires_completion_check"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("research_reports_pkey")),
        schema="public",
    )
    op.create_index(
        "research_reports_filter_hash_idx",
        "research_reports",
        ["filter_hash"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "research_reports_user_id_created_at_idx",
        "research_reports",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_table(
        "resource_entries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("organization", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("country_scope", sa.String(length=50), nullable=False),
        sa.Column("category", enum_type("resource_category"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "status", enum_type("publication_status"), server_default="draft", nullable=False
        ),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status <> 'published' OR (reviewed_by IS NOT NULL AND last_reviewed_at IS NOT NULL)",
            name=op.f("resource_entries_published_requires_review_check"),
        ),
        sa.CheckConstraint("url LIKE 'https://%%'", name=op.f("resource_entries_url_https_check")),
        sa.PrimaryKeyConstraint("id", name=op.f("resource_entries_pkey")),
        sa.UniqueConstraint("url", name="resource_entries_url_unique"),
        schema="public",
    )
    op.create_index(
        "resource_entries_category_title_idx",
        "resource_entries",
        ["category", "title"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("status = 'published'"),
    )
    op.create_index(
        "resource_entries_country_scope_idx",
        "resource_entries",
        ["country_scope"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "resource_entries_status_idx", "resource_entries", ["status"], unique=False, schema="public"
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("kind", enum_type("source_kind"), nullable=False),
        sa.Column("platform", enum_type("public_platform"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("policy_url", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "status", enum_type("connector_status"), server_default="not_configured", nullable=False
        ),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("config_version", sa.String(length=50), nullable=False),
        sa.Column("retention_policy", enum_type("retention_policy"), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safe_warning", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("sources_pkey")),
        sa.UniqueConstraint("source_key", name="sources_source_key_unique"),
        schema="public",
    )
    op.create_index(
        "sources_open_datapack_singleton_idx",
        "sources",
        ["kind"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("kind = 'open_datapack'"),
    )
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("role", enum_type("user_role"), server_default="registered_user", nullable=False),
        sa.Column(
            "onboarding_status",
            enum_type("onboarding_status"),
            server_default="not_started",
            nullable=False,
        ),
        sa.Column(
            "content_safety_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "display_name IS NULL OR length(display_name) BETWEEN 1 AND 80",
            name=op.f("user_profiles_display_name_length_check"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("user_profiles_pkey")),
        schema="public",
    )
    op.create_index(
        "user_profiles_role_idx", "user_profiles", ["role"], unique=False, schema="public"
    )
    op.create_table(
        "dataset_import_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_package_id", sa.UUID(), nullable=False),
        sa.Column("status", enum_type("job_state"), server_default="queued", nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("imported_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=op.f("dataset_import_runs_completion_after_start_check"),
        ),
        sa.CheckConstraint(
            "imported_count >= 0 AND skipped_count >= 0 AND error_count >= 0",
            name=op.f("dataset_import_runs_counts_non_negative_check"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_package_id"],
            ["public.dataset_packages.id"],
            name=op.f("dataset_import_runs_dataset_package_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("dataset_import_runs_pkey")),
        schema="public",
    )
    op.create_index(
        "dataset_import_runs_dataset_package_id_idx",
        "dataset_import_runs",
        ["dataset_package_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "dataset_import_runs_status_started_at_idx",
        "dataset_import_runs",
        ["status", "started_at"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "metric_buckets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("metric_key", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("interval", enum_type("metric_interval"), nullable=False),
        sa.Column(
            "bucket_start",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("observed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("relevant_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("likely_hate_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reviewed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("confirmed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=True),
        sa.Column(
            "coverage_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("filter_version", sa.String(length=50), nullable=False),
        sa.Column("sampling_disclosure", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "coverage_score IS NULL OR (coverage_score >= 0 AND coverage_score <= 1)",
            name=op.f("metric_buckets_coverage_score_range_check"),
        ),
        sa.CheckConstraint(
            "observed_count >= 0 AND relevant_count >= 0 AND likely_hate_count >= 0 "
            "AND reviewed_count >= 0 AND confirmed_count >= 0",
            name=op.f("metric_buckets_counts_non_negative_check"),
        ),
        sa.CheckConstraint(
            "relevant_count <= observed_count AND likely_hate_count <= relevant_count "
            "AND confirmed_count <= reviewed_count AND reviewed_count <= observed_count",
            name=op.f("metric_buckets_counts_nested_check"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["public.sources.id"],
            name=op.f("metric_buckets_source_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("metric_buckets_pkey")),
        sa.UniqueConstraint(
            "metric_key",
            "source_id",
            "interval",
            "bucket_start",
            "filter_version",
            name="metric_buckets_key_source_interval_bucket_filter_unique",
        ),
        schema="public",
    )
    op.create_index(
        "metric_buckets_metric_key_interval_bucket_start_idx",
        "metric_buckets",
        ["metric_key", "interval", sa.literal_column("bucket_start DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "metric_buckets_source_id_idx",
        "metric_buckets",
        ["source_id"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "source_seed_entries",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("registry_key", sa.String(length=200), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("entry_kind", enum_type("seed_entry_kind"), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("provider_reference", sa.Text(), nullable=False),
        sa.Column("query_family", sa.String(length=100), nullable=False),
        sa.Column("query_purpose", sa.Text(), nullable=False),
        sa.Column("sampling_stratum", enum_type("sampling_stratum"), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("country_scope", sa.String(length=50), nullable=True),
        sa.Column("item_cap", sa.Integer(), nullable=False),
        sa.Column(
            "approval_status",
            enum_type("approval_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("config_version", sa.String(length=50), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language ~ '^[a-z]{2}$'", name=op.f("source_seed_entries_language_format_check")
        ),
        sa.CheckConstraint(
            "item_cap > 0", name=op.f("source_seed_entries_item_cap_positive_check")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["public.sources.id"],
            name=op.f("source_seed_entries_source_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("source_seed_entries_pkey")),
        sa.UniqueConstraint(
            "registry_key",
            "config_version",
            name="source_seed_entries_registry_key_config_version_unique",
        ),
        schema="public",
    )
    op.create_index(
        "source_seed_entries_source_id_idx",
        "source_seed_entries",
        ["source_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "source_seed_entries_source_id_sampling_stratum_idx",
        "source_seed_entries",
        ["source_id", "sampling_stratum"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("approval_status = 'approved'"),
    )
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_seed_entry_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("mode", enum_type("collection_mode"), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("status", enum_type("job_state"), server_default="queued", nullable=False),
        sa.Column(
            "counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "coverage_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=op.f("collection_runs_completion_after_start_check"),
        ),
        sa.CheckConstraint(
            "window_end IS NULL OR window_start IS NULL OR window_end >= window_start",
            name=op.f("collection_runs_window_ordered_check"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["public.sources.id"],
            name=op.f("collection_runs_source_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_seed_entry_id"],
            ["public.source_seed_entries.id"],
            name=op.f("collection_runs_source_seed_entry_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("collection_runs_pkey")),
        sa.UniqueConstraint("idempotency_key", name="collection_runs_idempotency_key_unique"),
        schema="public",
    )
    op.create_index(
        "collection_runs_source_id_started_at_idx",
        "collection_runs",
        ["source_id", sa.literal_column("started_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "collection_runs_source_seed_entry_id_idx",
        "collection_runs",
        ["source_seed_entry_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "collection_runs_status_idx", "collection_runs", ["status"], unique=False, schema="public"
    )
    op.create_table(
        "content_items",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_item_id", sa.String(length=400), nullable=False),
        sa.Column("collection_run_id", sa.UUID(), nullable=True),
        sa.Column("source_seed_entry_id", sa.UUID(), nullable=True),
        sa.Column("content_kind", enum_type("content_kind"), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("dataset_package_id", sa.UUID(), nullable=True),
        sa.Column("dataset_import_run_id", sa.UUID(), nullable=True),
        sa.Column("dataset_row_id", sa.String(length=400), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("permitted_excerpt", sa.Text(), nullable=True),
        sa.Column("text_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("normalization_version", sa.String(length=50), nullable=True),
        sa.Column("raw_object_key", sa.Text(), nullable=True),
        sa.Column("publisher_or_container", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("geographic_scope", sa.String(length=50), nullable=True),
        sa.Column(
            "source_status",
            enum_type("source_availability"),
            server_default="available",
            nullable=False,
        ),
        sa.Column("is_fixture", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("submitted_origin", sa.UUID(), nullable=True),
        sa.Column(
            "effective_review_state",
            enum_type("review_state"),
            server_default="model_only",
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "canonical_url IS NULL OR canonical_url ~ '^https?://'",
            name=op.f("content_items_canonical_url_scheme_check"),
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name=op.f("content_items_content_hash_format_check")
        ),
        sa.CheckConstraint(
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'",
            name=op.f("content_items_country_code_format_check"),
        ),
        sa.CheckConstraint(
            "(dataset_package_id IS NULL) = (dataset_row_id IS NULL)",
            name=op.f("content_items_dataset_provenance_complete_check"),
        ),
        sa.ForeignKeyConstraint(
            ["collection_run_id"],
            ["public.collection_runs.id"],
            name=op.f("content_items_collection_run_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_import_run_id"],
            ["public.dataset_import_runs.id"],
            name=op.f("content_items_dataset_import_run_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_package_id"],
            ["public.dataset_packages.id"],
            name=op.f("content_items_dataset_package_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["public.sources.id"],
            name=op.f("content_items_source_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_seed_entry_id"],
            ["public.source_seed_entries.id"],
            name=op.f("content_items_source_seed_entry_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("content_items_pkey")),
        sa.UniqueConstraint(
            "source_id", "source_item_id", name="content_items_source_id_source_item_id_unique"
        ),
        schema="public",
    )
    op.create_index(
        "content_items_canonical_url_idx",
        "content_items",
        ["canonical_url"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_collection_run_id_idx",
        "content_items",
        ["collection_run_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_content_kind_observed_at_idx",
        "content_items",
        ["content_kind", sa.literal_column("observed_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_country_code_idx",
        "content_items",
        ["country_code"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("country_code IS NOT NULL"),
    )
    op.create_index(
        "content_items_dataset_import_run_id_idx",
        "content_items",
        ["dataset_import_run_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_dataset_package_id_dataset_row_id_idx",
        "content_items",
        ["dataset_package_id", "dataset_row_id"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("dataset_package_id IS NOT NULL"),
    )
    op.create_index(
        "content_items_dataset_package_id_idx",
        "content_items",
        ["dataset_package_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_observed_at_id_idx",
        "content_items",
        [sa.literal_column("observed_at DESC"), sa.literal_column("id DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_published_at_id_idx",
        "content_items",
        [sa.literal_column("published_at DESC"), sa.literal_column("id DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_source_id_observed_at_idx",
        "content_items",
        ["source_id", sa.literal_column("observed_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_source_seed_entry_id_idx",
        "content_items",
        ["source_seed_entry_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_items_submitted_origin_idx",
        "content_items",
        ["submitted_origin"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("submitted_origin IS NOT NULL"),
    )
    op.create_table(
        "content_submissions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("submitted_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("content_item_id", sa.UUID(), nullable=True),
        sa.Column(
            "status", enum_type("submission_status"), server_default="processing", nullable=False
        ),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status <> 'analyzed' OR content_item_id IS NOT NULL",
            name=op.f("content_submissions_analyzed_requires_item_check"),
        ),
        sa.CheckConstraint(
            "submitted_url ~ '^https?://'",
            name=op.f("content_submissions_submitted_url_scheme_check"),
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("content_submissions_content_item_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("content_submissions_pkey")),
        schema="public",
    )
    op.create_index(
        "content_submissions_content_item_id_idx",
        "content_submissions",
        ["content_item_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_submissions_status_idx",
        "content_submissions",
        ["status"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "content_submissions_user_id_canonical_url_idx",
        "content_submissions",
        ["user_id", "canonical_url"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("canonical_url IS NOT NULL"),
    )
    op.create_index(
        "content_submissions_user_id_submitted_at_idx",
        "content_submissions",
        ["user_id", sa.literal_column("submitted_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_table(
        "news_event_links",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("related_metric_key", sa.String(length=100), nullable=False),
        sa.Column("relation_score", sa.Float(), nullable=False),
        sa.Column("relation_basis", enum_type("relation_basis"), nullable=False),
        sa.Column(
            "review_state",
            enum_type("relation_review_state"),
            server_default="unreviewed",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relation_score >= 0 AND relation_score <= 1",
            name=op.f("news_event_links_relation_score_range_check"),
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("news_event_links_content_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("news_event_links_pkey")),
        sa.UniqueConstraint(
            "content_item_id",
            "related_metric_key",
            name="news_event_links_content_item_id_related_metric_key_unique",
        ),
        schema="public",
    )
    op.create_index(
        "news_event_links_related_metric_key_idx",
        "news_event_links",
        ["related_metric_key"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("normalization_version", sa.String(length=50), nullable=True),
        sa.Column("relevance", enum_type("relevance"), nullable=False),
        sa.Column("stance", enum_type("stance"), nullable=False),
        sa.Column(
            "hate_types",
            postgresql.ARRAY(enum_type("hate_type")),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("severity", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "narrative_tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence_tier", enum_type("confidence_tier"), nullable=False),
        sa.Column("confidence_threshold_version", sa.String(length=50), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("requires_review", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("review_reason", sa.String(length=100), nullable=True),
        sa.Column(
            "inference_status",
            enum_type("inference_status"),
            server_default="succeeded",
            nullable=False,
        ),
        sa.Column("inferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "inference_status = 'succeeded' OR stance <> 'likely_anti_muslim'",
            name=op.f("predictions_unsuccessful_inference_makes_no_claim_check"),
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name=op.f("predictions_score_range_check")),
        sa.CheckConstraint(
            "severity >= 0 AND severity <= 3", name=op.f("predictions_severity_range_check")
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("predictions_content_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("predictions_pkey")),
        sa.UniqueConstraint(
            "content_item_id",
            "model_name",
            "model_version",
            "prompt_version",
            name="predictions_content_item_model_prompt_version_unique",
        ),
        schema="public",
    )
    op.create_index(
        "predictions_confidence_tier_idx",
        "predictions",
        ["confidence_tier"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "predictions_content_item_id_created_at_idx",
        "predictions",
        ["content_item_id", sa.literal_column("created_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_index(
        "predictions_requires_review_idx",
        "predictions",
        ["created_at"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("requires_review"),
    )
    op.create_table(
        "prepared_platform_reports",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("platform_policy_id", sa.UUID(), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=False),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column(
            "status", enum_type("prepared_report_status"), server_default="prepared", nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", enum_type("prepared_report_outcome"), nullable=True),
        sa.Column("outcome_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR status <> 'prepared'",
            name=op.f("prepared_platform_reports_outcome_requires_submission_check"),
        ),
        sa.CheckConstraint(
            "status <> 'submitted' OR submitted_at IS NOT NULL",
            name=op.f("prepared_platform_reports_submitted_requires_timestamp_check"),
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("prepared_platform_reports_content_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["platform_policy_id"],
            ["public.platform_policies.id"],
            name=op.f("prepared_platform_reports_platform_policy_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("prepared_platform_reports_pkey")),
        sa.UniqueConstraint(
            "user_id",
            "content_item_id",
            "platform",
            name="prepared_platform_reports_user_item_platform_unique",
        ),
        schema="public",
    )
    op.create_index(
        "prepared_platform_reports_content_item_id_idx",
        "prepared_platform_reports",
        ["content_item_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "prepared_platform_reports_platform_policy_id_idx",
        "prepared_platform_reports",
        ["platform_policy_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "prepared_platform_reports_user_id_created_at_idx",
        "prepared_platform_reports",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_table(
        "policy_matches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=False),
        sa.Column("platform_policy_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence_tier", enum_type("confidence_tier"), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1", name=op.f("policy_matches_score_range_check")
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("policy_matches_content_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["platform_policy_id"],
            ["public.platform_policies.id"],
            name=op.f("policy_matches_platform_policy_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["public.predictions.id"],
            name=op.f("policy_matches_prediction_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("policy_matches_pkey")),
        sa.UniqueConstraint(
            "content_item_id",
            "platform_policy_id",
            "model_version",
            name="policy_matches_item_policy_model_version_unique",
        ),
        schema="public",
    )
    op.create_index(
        "policy_matches_content_item_id_idx",
        "policy_matches",
        ["content_item_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "policy_matches_platform_policy_id_idx",
        "policy_matches",
        ["platform_policy_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "policy_matches_prediction_id_idx",
        "policy_matches",
        ["prediction_id"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=False),
        sa.Column("task_type", enum_type("review_task_type"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", enum_type("review_task_status"), server_default="open", nullable=False),
        sa.Column("assigned_to", sa.UUID(), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status <> 'claimed' OR assigned_to IS NOT NULL",
            name=op.f("review_tasks_claimed_requires_assignee_check"),
        ),
        sa.CheckConstraint(
            "status <> 'completed' OR completed_at IS NOT NULL",
            name=op.f("review_tasks_completed_requires_timestamp_check"),
        ),
        sa.CheckConstraint("priority >= 0", name=op.f("review_tasks_priority_non_negative_check")),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("review_tasks_content_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["public.predictions.id"],
            name=op.f("review_tasks_prediction_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("review_tasks_pkey")),
        schema="public",
    )
    op.create_index(
        "review_tasks_assigned_to_idx",
        "review_tasks",
        ["assigned_to"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "review_tasks_content_item_id_idx",
        "review_tasks",
        ["content_item_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "review_tasks_prediction_id_task_type_idx",
        "review_tasks",
        ["prediction_id", "task_type"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("status IN ('open', 'claimed')"),
    )
    op.create_index(
        "review_tasks_status_priority_created_at_idx",
        "review_tasks",
        ["status", sa.literal_column("priority DESC"), "created_at"],
        unique=False,
        schema="public",
    )
    op.create_table(
        "classification_disputes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("content_item_id", sa.UUID(), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", enum_type("dispute_status"), server_default="open", nullable=False),
        sa.Column("review_task_id", sa.UUID(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status NOT IN ('resolved_upheld', 'resolved_corrected') OR resolved_at IS NOT NULL",
            name=op.f("classification_disputes_resolved_requires_timestamp_check"),
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name=op.f("classification_disputes_resolution_after_creation_check"),
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["public.content_items.id"],
            name=op.f("classification_disputes_content_item_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["public.predictions.id"],
            name=op.f("classification_disputes_prediction_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["review_task_id"],
            ["public.review_tasks.id"],
            name=op.f("classification_disputes_review_task_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("classification_disputes_pkey")),
        schema="public",
    )
    op.create_index(
        "classification_disputes_content_item_id_idx",
        "classification_disputes",
        ["content_item_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "classification_disputes_prediction_id_idx",
        "classification_disputes",
        ["prediction_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "classification_disputes_review_task_id_idx",
        "classification_disputes",
        ["review_task_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "classification_disputes_user_id_content_item_id_idx",
        "classification_disputes",
        ["user_id", "content_item_id"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("status IN ('open', 'in_review')"),
    )
    op.create_index(
        "classification_disputes_user_id_created_at_idx",
        "classification_disputes",
        ["user_id", sa.literal_column("created_at DESC")],
        unique=False,
        schema="public",
    )
    op.create_table(
        "review_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("review_task_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column("decision", enum_type("review_decision"), nullable=False),
        sa.Column("corrected_labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "is_training_candidate", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(decision = 'corrected') = (corrected_labels IS NOT NULL)",
            name=op.f("review_events_corrected_labels_match_decision_check"),
        ),
        sa.ForeignKeyConstraint(
            ["review_task_id"],
            ["public.review_tasks.id"],
            name=op.f("review_events_review_task_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("review_events_pkey")),
        schema="public",
    )
    op.create_index(
        "review_events_review_task_id_created_at_idx",
        "review_events",
        ["review_task_id", "created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "review_events_reviewer_id_idx",
        "review_events",
        ["reviewer_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("review_events_reviewer_id_idx", table_name="review_events", schema="public")
    op.drop_index(
        "review_events_review_task_id_created_at_idx", table_name="review_events", schema="public"
    )
    op.drop_table("review_events", schema="public")
    op.drop_index(
        "classification_disputes_user_id_created_at_idx",
        table_name="classification_disputes",
        schema="public",
    )
    op.drop_index(
        "classification_disputes_user_id_content_item_id_idx",
        table_name="classification_disputes",
        schema="public",
        postgresql_where=sa.text("status IN ('open', 'in_review')"),
    )
    op.drop_index(
        "classification_disputes_review_task_id_idx",
        table_name="classification_disputes",
        schema="public",
    )
    op.drop_index(
        "classification_disputes_prediction_id_idx",
        table_name="classification_disputes",
        schema="public",
    )
    op.drop_index(
        "classification_disputes_content_item_id_idx",
        table_name="classification_disputes",
        schema="public",
    )
    op.drop_table("classification_disputes", schema="public")
    op.drop_index(
        "review_tasks_status_priority_created_at_idx", table_name="review_tasks", schema="public"
    )
    op.drop_index(
        "review_tasks_prediction_id_task_type_idx",
        table_name="review_tasks",
        schema="public",
        postgresql_where=sa.text("status IN ('open', 'claimed')"),
    )
    op.drop_index("review_tasks_content_item_id_idx", table_name="review_tasks", schema="public")
    op.drop_index("review_tasks_assigned_to_idx", table_name="review_tasks", schema="public")
    op.drop_table("review_tasks", schema="public")
    op.drop_index("policy_matches_prediction_id_idx", table_name="policy_matches", schema="public")
    op.drop_index(
        "policy_matches_platform_policy_id_idx", table_name="policy_matches", schema="public"
    )
    op.drop_index(
        "policy_matches_content_item_id_idx", table_name="policy_matches", schema="public"
    )
    op.drop_table("policy_matches", schema="public")
    op.drop_index(
        "prepared_platform_reports_user_id_created_at_idx",
        table_name="prepared_platform_reports",
        schema="public",
    )
    op.drop_index(
        "prepared_platform_reports_platform_policy_id_idx",
        table_name="prepared_platform_reports",
        schema="public",
    )
    op.drop_index(
        "prepared_platform_reports_content_item_id_idx",
        table_name="prepared_platform_reports",
        schema="public",
    )
    op.drop_table("prepared_platform_reports", schema="public")
    op.drop_index(
        "predictions_requires_review_idx",
        table_name="predictions",
        schema="public",
        postgresql_where=sa.text("requires_review"),
    )
    op.drop_index(
        "predictions_content_item_id_created_at_idx", table_name="predictions", schema="public"
    )
    op.drop_index("predictions_confidence_tier_idx", table_name="predictions", schema="public")
    op.drop_table("predictions", schema="public")
    op.drop_index(
        "news_event_links_related_metric_key_idx", table_name="news_event_links", schema="public"
    )
    op.drop_table("news_event_links", schema="public")
    op.drop_index(
        "content_submissions_user_id_submitted_at_idx",
        table_name="content_submissions",
        schema="public",
    )
    op.drop_index(
        "content_submissions_user_id_canonical_url_idx",
        table_name="content_submissions",
        schema="public",
        postgresql_where=sa.text("canonical_url IS NOT NULL"),
    )
    op.drop_index(
        "content_submissions_status_idx", table_name="content_submissions", schema="public"
    )
    op.drop_index(
        "content_submissions_content_item_id_idx", table_name="content_submissions", schema="public"
    )
    op.drop_table("content_submissions", schema="public")
    op.drop_index(
        "content_items_submitted_origin_idx",
        table_name="content_items",
        schema="public",
        postgresql_where=sa.text("submitted_origin IS NOT NULL"),
    )
    op.drop_index(
        "content_items_source_seed_entry_id_idx", table_name="content_items", schema="public"
    )
    op.drop_index(
        "content_items_source_id_observed_at_idx", table_name="content_items", schema="public"
    )
    op.drop_index("content_items_published_at_id_idx", table_name="content_items", schema="public")
    op.drop_index("content_items_observed_at_id_idx", table_name="content_items", schema="public")
    op.drop_index(
        "content_items_dataset_package_id_idx", table_name="content_items", schema="public"
    )
    op.drop_index(
        "content_items_dataset_package_id_dataset_row_id_idx",
        table_name="content_items",
        schema="public",
        postgresql_where=sa.text("dataset_package_id IS NOT NULL"),
    )
    op.drop_index(
        "content_items_dataset_import_run_id_idx", table_name="content_items", schema="public"
    )
    op.drop_index(
        "content_items_country_code_idx",
        table_name="content_items",
        schema="public",
        postgresql_where=sa.text("country_code IS NOT NULL"),
    )
    op.drop_index(
        "content_items_content_kind_observed_at_idx", table_name="content_items", schema="public"
    )
    op.drop_index(
        "content_items_collection_run_id_idx", table_name="content_items", schema="public"
    )
    op.drop_index("content_items_canonical_url_idx", table_name="content_items", schema="public")
    op.drop_table("content_items", schema="public")
    op.drop_index("collection_runs_status_idx", table_name="collection_runs", schema="public")
    op.drop_index(
        "collection_runs_source_seed_entry_id_idx", table_name="collection_runs", schema="public"
    )
    op.drop_index(
        "collection_runs_source_id_started_at_idx", table_name="collection_runs", schema="public"
    )
    op.drop_table("collection_runs", schema="public")
    op.drop_index(
        "source_seed_entries_source_id_sampling_stratum_idx",
        table_name="source_seed_entries",
        schema="public",
        postgresql_where=sa.text("approval_status = 'approved'"),
    )
    op.drop_index(
        "source_seed_entries_source_id_idx", table_name="source_seed_entries", schema="public"
    )
    op.drop_table("source_seed_entries", schema="public")
    op.drop_index("metric_buckets_source_id_idx", table_name="metric_buckets", schema="public")
    op.drop_index(
        "metric_buckets_metric_key_interval_bucket_start_idx",
        table_name="metric_buckets",
        schema="public",
    )
    op.drop_table("metric_buckets", schema="public")
    op.drop_index(
        "dataset_import_runs_status_started_at_idx",
        table_name="dataset_import_runs",
        schema="public",
    )
    op.drop_index(
        "dataset_import_runs_dataset_package_id_idx",
        table_name="dataset_import_runs",
        schema="public",
    )
    op.drop_table("dataset_import_runs", schema="public")
    op.drop_index("user_profiles_role_idx", table_name="user_profiles", schema="public")
    op.drop_table("user_profiles", schema="public")
    op.drop_index(
        "sources_open_datapack_singleton_idx",
        table_name="sources",
        schema="public",
        postgresql_where=sa.text("kind = 'open_datapack'"),
    )
    op.drop_table("sources", schema="public")
    op.drop_index("resource_entries_status_idx", table_name="resource_entries", schema="public")
    op.drop_index(
        "resource_entries_country_scope_idx", table_name="resource_entries", schema="public"
    )
    op.drop_index(
        "resource_entries_category_title_idx",
        table_name="resource_entries",
        schema="public",
        postgresql_where=sa.text("status = 'published'"),
    )
    op.drop_table("resource_entries", schema="public")
    op.drop_index(
        "research_reports_user_id_created_at_idx", table_name="research_reports", schema="public"
    )
    op.drop_index(
        "research_reports_filter_hash_idx", table_name="research_reports", schema="public"
    )
    op.drop_table("research_reports", schema="public")
    op.drop_index(
        "platform_policies_platform_status_idx", table_name="platform_policies", schema="public"
    )
    op.drop_table("platform_policies", schema="public")
    op.drop_index(
        "insight_snapshots_generated_at_idx", table_name="insight_snapshots", schema="public"
    )
    op.drop_table("insight_snapshots", schema="public")
    op.drop_index(
        "dataset_packages_approval_status_idx", table_name="dataset_packages", schema="public"
    )
    op.drop_table("dataset_packages", schema="public")
    op.drop_index(
        "contribution_events_user_id_created_at_idx",
        table_name="contribution_events",
        schema="public",
    )
    op.drop_index(
        "contribution_events_contribution_id_idx", table_name="contribution_events", schema="public"
    )
    op.drop_table("contribution_events", schema="public")
    _drop_enum_types()
