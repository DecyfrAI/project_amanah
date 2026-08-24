"""Sampling strata on metric buckets, plus the image-evidence catalog.

Two things arrive here, both required by Milestone 4.

*Sampling strata.* `metric_buckets` gains `sampling_stratum` and takes it into
the bucket's identity. `spec.md` section 9.5 and B-S15.9 both forbid pooling an
enriched seed sample with ordinary monitoring, and a column that is not part of
the unique key would let two strata upsert onto one row and become a single
figure. Existing rows default to `ordinary_monitoring`: every bucket written
before this migration came from unseeded collection, so the default states what
was already true rather than guessing.

*Image evidence.* `image_examples` and `image_classifications` implement ADR
0007. Neither table has a column for image bytes. The bytes live in object
storage, Postgres holds the path, digest, media type, size, the annotations the
source dataset shipped, and — in the second table — what Amanah's own classifier
concluded. The two are separate tables so a dataset's label and a prediction can
never be read out of one column by accident.

Both new tables get the boundary every product table already has: row-level
security forced on, base grants revoked, and a projection that a verified reader
may select from. The projection carries no storage path, so a signed URL can only
be minted server-side.

Revision ID: 0005_analysis_and_image_corpus
Revises: 0004_collection_pipeline
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from amanah.db.models.images import ALLOWED_IMAGE_MIME_TYPES

revision: str = "0005_analysis_and_image_corpus"
down_revision: str | None = "0004_collection_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Projections added here.
NEW_VIEWS = ("authenticated_image_examples",)

#: Recreated here because its base table gained a column. A view is not updated
#: by `ALTER TABLE`, so the projection has to be dropped and rebuilt or it will
#: keep serving the old column list.
REBUILT_VIEWS = ("authenticated_metric_buckets",)

#: The unique constraint `metric_buckets` carried before this migration, and the
#: one it carries after. Named explicitly so the downgrade restores exactly the
#: shape `0001` created.
_OLD_BUCKET_UNIQUE = "metric_buckets_key_source_interval_bucket_filter_unique"
_NEW_BUCKET_UNIQUE = "metric_buckets_key_source_stratum_interval_bucket_filter_unique"

_MIME_TYPE_LIST = ", ".join(f"'{mime_type}'" for mime_type in ALLOWED_IMAGE_MIME_TYPES)


def _enum(name: str) -> postgresql.ENUM:
    """Reference an enum type an earlier migration created."""
    return postgresql.ENUM(name=name, create_type=False, schema="public")


def _add_sampling_stratum() -> None:
    """Make the stratum part of a bucket's identity."""
    op.add_column(
        "metric_buckets",
        sa.Column(
            "sampling_stratum",
            _enum("sampling_stratum"),
            nullable=False,
            server_default="ordinary_monitoring",
        ),
        schema="public",
    )
    op.drop_constraint(_OLD_BUCKET_UNIQUE, "metric_buckets", schema="public")
    op.create_unique_constraint(
        _NEW_BUCKET_UNIQUE,
        "metric_buckets",
        [
            "metric_key",
            "source_id",
            "sampling_stratum",
            "interval",
            "bucket_start",
            "filter_version",
        ],
        schema="public",
    )
    op.create_index(
        "metric_buckets_metric_key_sampling_stratum_idx",
        "metric_buckets",
        ["metric_key", "sampling_stratum"],
        schema="public",
    )


#: `0003` created this view over the old column list. Rebuilt verbatim except for
#: the added stratum, so a reader can see the whole projection in one place rather
#: than reconstructing it from two migrations.
_METRIC_BUCKET_VIEW = """
CREATE VIEW public.authenticated_metric_buckets AS
SELECT
  bucket.id,
  bucket.metric_key,
  bucket.source_id,
  source.name                    AS source_name,
  source.platform::text          AS platform,
  bucket.sampling_stratum::text  AS sampling_stratum,
  bucket.interval::text          AS interval,
  bucket.bucket_start,
  bucket.observed_count,
  bucket.relevant_count,
  bucket.likely_hate_count,
  bucket.reviewed_count,
  bucket.confirmed_count,
  bucket.coverage_score,
  bucket.coverage_warnings,
  bucket.filter_version,
  bucket.sampling_disclosure
FROM public.metric_buckets AS bucket
JOIN public.sources AS source ON source.id = bucket.source_id
WHERE public.amanah_current_user_id() IS NOT NULL;
"""

#: The `0003` definition, restored on downgrade.
_METRIC_BUCKET_VIEW_WITHOUT_STRATUM = """
CREATE VIEW public.authenticated_metric_buckets AS
SELECT
  bucket.id,
  bucket.metric_key,
  bucket.source_id,
  source.name           AS source_name,
  source.platform::text AS platform,
  bucket.interval::text AS interval,
  bucket.bucket_start,
  bucket.observed_count,
  bucket.relevant_count,
  bucket.likely_hate_count,
  bucket.reviewed_count,
  bucket.confirmed_count,
  bucket.coverage_score,
  bucket.coverage_warnings,
  bucket.filter_version,
  bucket.sampling_disclosure
FROM public.metric_buckets AS bucket
JOIN public.sources AS source ON source.id = bucket.source_id
WHERE public.amanah_current_user_id() IS NOT NULL;
"""


def _widen_insight_data_version() -> None:
    """Make room for a fact-bundle digest.

    `0001` sized this for a version label. It now holds the SHA-256 of the exact
    facts a narrative was generated from, which is what makes newly collected data
    a cache miss rather than a stale summary served over fresh figures (B-S15.10).
    A 64-character digest does not fit in 50.
    """
    op.alter_column(
        "insight_snapshots",
        "data_version",
        existing_type=sa.String(length=50),
        type_=sa.String(length=64),
        existing_nullable=False,
        schema="public",
    )


def _rebuild_metric_bucket_view(definition: str) -> None:
    """Replace the projection so it exposes the current column list."""
    op.execute("DROP VIEW IF EXISTS public.authenticated_metric_buckets")
    op.execute(definition)
    op.execute("GRANT SELECT ON public.authenticated_metric_buckets TO authenticated")


def _create_image_examples() -> None:
    op.create_table(
        "image_examples",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_package_id", sa.UUID(), nullable=False),
        sa.Column("dataset_row_id", sa.String(length=400), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("alt_text", sa.Text(), nullable=False),
        sa.Column("form_note", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "annotation_hate_types",
            postgresql.ARRAY(_enum("hate_type")),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("annotation_severity", sa.SmallInteger(), nullable=True),
        sa.Column("annotation_note", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "publication_status",
            _enum("publication_status"),
            server_default="draft",
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
        sa.PrimaryKeyConstraint("id", name="image_examples_pkey"),
        sa.ForeignKeyConstraint(
            ["dataset_package_id"],
            ["public.dataset_packages.id"],
            name="image_examples_dataset_package_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "dataset_package_id",
            "dataset_row_id",
            name="image_examples_dataset_package_id_dataset_row_id_unique",
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="image_examples_sha256_format_check"),
        sa.CheckConstraint("byte_size > 0", name="image_examples_byte_size_positive_check"),
        sa.CheckConstraint(
            f"mime_type IN ({_MIME_TYPE_LIST})", name="image_examples_mime_type_allowed_check"
        ),
        sa.CheckConstraint(
            "annotation_severity IS NULL "
            "OR (annotation_severity >= 0 AND annotation_severity <= 3)",
            name="image_examples_annotation_severity_range_check",
        ),
        sa.CheckConstraint(
            "length(btrim(alt_text)) > 0", name="image_examples_alt_text_present_check"
        ),
        schema="public",
    )
    op.create_index(
        "image_examples_dataset_package_id_idx",
        "image_examples",
        ["dataset_package_id"],
        schema="public",
    )
    op.create_index(
        "image_examples_publication_status_idx",
        "image_examples",
        ["publication_status"],
        schema="public",
        postgresql_where=sa.text("publication_status = 'published'"),
    )


def _create_image_classifications() -> None:
    op.create_table(
        "image_classifications",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("image_example_id", sa.UUID(), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("relevance", _enum("relevance"), nullable=False),
        sa.Column("stance", _enum("stance"), nullable=False),
        sa.Column(
            "hate_types",
            postgresql.ARRAY(_enum("hate_type")),
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
        sa.Column("confidence_tier", _enum("confidence_tier"), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("requires_review", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "inference_status",
            _enum("inference_status"),
            server_default="succeeded",
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("inferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="image_classifications_pkey"),
        sa.ForeignKeyConstraint(
            ["image_example_id"],
            ["public.image_examples.id"],
            name="image_classifications_image_example_id_fkey",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "image_example_id",
            "model_name",
            "model_version",
            "prompt_version",
            name="image_classifications_image_model_prompt_version_unique",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1", name="image_classifications_score_range_check"
        ),
        sa.CheckConstraint(
            "severity >= 0 AND severity <= 3", name="image_classifications_severity_range_check"
        ),
        sa.CheckConstraint(
            "inference_status = 'succeeded' OR stance <> 'likely_anti_muslim'",
            name="image_classifications_unsuccessful_makes_no_claim_check",
        ),
        schema="public",
    )
    op.create_index(
        "image_classifications_image_example_id_created_at_idx",
        "image_classifications",
        ["image_example_id", sa.text("created_at DESC")],
        schema="public",
    )


def _secure_image_tables() -> None:
    """Deny by default, then name exactly who may reach what.

    A base-role reader gets the catalog through the projection below and never
    the table, so `storage_path` stays unreachable from a query. Writes are
    administrator-only: the corpus is curated, not user-generated.
    """
    for table in ("image_examples", "image_classifications"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON public.{table} FROM anon, PUBLIC, authenticated")

    op.execute(
        "CREATE POLICY image_examples_administrator_all ON public.image_examples "
        "FOR ALL TO authenticated "
        "USING (public.amanah_is_administrator()) "
        "WITH CHECK (public.amanah_is_administrator())"
    )
    op.execute(
        "CREATE POLICY image_classifications_administrator_all ON public.image_classifications "
        "FOR ALL TO authenticated "
        "USING (public.amanah_is_administrator()) "
        "WITH CHECK (public.amanah_is_administrator())"
    )


_IMAGE_VIEW = """
-- The authenticated image catalog. Deliberately carries no `storage_path`: a
-- reader receives a short-lived signed URL minted server-side, never a durable
-- location, so one saved response cannot become an open gallery (ADR 0007).
--
-- Dataset annotations and Amanah's own classification are projected as distinct
-- columns under distinct names. Collapsing them would present someone else's
-- dataset label as a finding this product made.
CREATE VIEW public.authenticated_image_examples WITH (security_barrier = true) AS
SELECT
  example.id,
  example.title,
  example.alt_text,
  example.form_note,
  example.mime_type,
  example.byte_size,
  example.sha256,
  example.annotation_hate_types,
  example.annotation_severity,
  example.annotation_note,
  package.provider               AS dataset_provider,
  package.name                   AS dataset_name,
  package.version                AS dataset_version,
  package.license_id             AS dataset_license_id,
  package.schema_mapping_version AS dataset_schema_mapping_version,
  package.approval_status::text  AS dataset_approval_status,
  package.approved_by            AS dataset_reviewer,
  latest.score,
  latest.narrative_tags,
  latest.rationale,
  latest.relevance::text         AS relevance,
  latest.stance::text            AS stance,
  latest.confidence_tier::text   AS confidence_tier,
  latest.severity                AS predicted_severity,
  latest.hate_types              AS predicted_hate_types,
  latest.requires_review,
  latest.model_name,
  latest.model_version,
  latest.taxonomy_version,
  example.created_at
FROM public.image_examples AS example
JOIN public.dataset_packages AS package ON package.id = example.dataset_package_id
LEFT JOIN LATERAL (
  -- The current classification is the newest successful one. Superseded
  -- executions stay as history rather than being overwritten.
  SELECT
    classification.score, classification.narrative_tags, classification.rationale,
    classification.relevance, classification.stance, classification.confidence_tier,
    classification.severity, classification.hate_types, classification.requires_review,
    classification.model_name, classification.model_version, classification.taxonomy_version
  FROM public.image_classifications AS classification
  WHERE classification.image_example_id = example.id
    AND classification.inference_status = 'succeeded'
  ORDER BY classification.created_at DESC, classification.id DESC
  LIMIT 1
) AS latest ON TRUE
WHERE example.publication_status = 'published'
  AND public.amanah_current_user_id() IS NOT NULL;
"""


def upgrade() -> None:
    _add_sampling_stratum()
    _rebuild_metric_bucket_view(_METRIC_BUCKET_VIEW)
    _widen_insight_data_version()
    _create_image_examples()
    _create_image_classifications()
    _secure_image_tables()
    op.execute(_IMAGE_VIEW)
    for view in NEW_VIEWS:
        op.execute(f"GRANT SELECT ON public.{view} TO authenticated")


def downgrade() -> None:
    for view in reversed(NEW_VIEWS):
        op.execute(f"DROP VIEW IF EXISTS public.{view}")

    op.execute(
        "DROP POLICY IF EXISTS image_classifications_administrator_all "
        "ON public.image_classifications"
    )
    op.execute("DROP POLICY IF EXISTS image_examples_administrator_all ON public.image_examples")
    op.drop_index(
        "image_classifications_image_example_id_created_at_idx",
        table_name="image_classifications",
        schema="public",
    )
    op.drop_table("image_classifications", schema="public")
    op.drop_index(
        "image_examples_publication_status_idx", table_name="image_examples", schema="public"
    )
    op.drop_index(
        "image_examples_dataset_package_id_idx", table_name="image_examples", schema="public"
    )
    op.drop_table("image_examples", schema="public")

    op.drop_index(
        "metric_buckets_metric_key_sampling_stratum_idx",
        table_name="metric_buckets",
        schema="public",
    )
    # Narrowing can truncate, so any digest that will not fit is removed rather
    # than silently cut into a value that points at no bundle.
    op.execute("DELETE FROM public.insight_snapshots WHERE length(data_version) > 50")
    op.alter_column(
        "insight_snapshots",
        "data_version",
        existing_type=sa.String(length=64),
        type_=sa.String(length=50),
        existing_nullable=False,
        schema="public",
    )

    # The view depends on the column, so it goes before the column does.
    _rebuild_metric_bucket_view(_METRIC_BUCKET_VIEW_WITHOUT_STRATUM)
    op.drop_constraint(_NEW_BUCKET_UNIQUE, "metric_buckets", schema="public")
    op.create_unique_constraint(
        _OLD_BUCKET_UNIQUE,
        "metric_buckets",
        ["metric_key", "source_id", "interval", "bucket_start", "filter_version"],
        schema="public",
    )
    op.drop_column("metric_buckets", "sampling_stratum", schema="public")
