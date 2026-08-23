"""Collection pipeline: job queue, run leases, dedupe keys, and admin projections.

Three things arrive here.

*Work state.* `background_jobs` is the queue a worker claims from, one row per
checkpointed pipeline stage. `collection_runs` gains the same lease, attempt, and
dead-letter columns, so a run whose worker dies is recoverable rather than merely
stuck. Both carry their invariants as constraints rather than as comments: a
running row must hold a lease, a terminal row must have a completion time, and a
dead-lettered row must actually have failed.

*Dedupe keys.* `content_items` gains `canonical_url_key` and `headline_key`, the
two news dedupe forms `spec.md` section 10.5 requires, each behind a unique index
restricted to news articles. Deduplication is therefore a database guarantee: an
importer that forgets to look first is refused rather than silently doubling the
denominator of every rate computed over the table.

*Visibility.* `authenticated_collection_runs` and `authenticated_background_jobs`
project run and job state for administrators only; `authenticated_news` projects
the context news stream for any verified reader. Base tables stay ungranted, so
these views remain the only way in, and none of them has a column for a provider
payload, a queue message, a lease owner, or an opaque provider-side identifier.

Revision ID: 0004_collection_pipeline
Revises: 0003_projections_and_rls
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from amanah.domain.enums import JobStage

revision: str = "0004_collection_pipeline"
down_revision: str | None = "0003_projections_and_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Projections added here, in creation order.
NEW_VIEWS = (
    "authenticated_news",
    "authenticated_collection_runs",
    "authenticated_background_jobs",
)

_NEWS_VIEW = """
-- The context news stream behind GET /v1/news. Deliberately carries no hate
-- label, model score, severity, or review state: an ingested article is
-- published journalism that coincides with a monitoring window, never an Amanah
-- finding. Classified news *items* are a different surface, read through
-- `authenticated_items`.
CREATE VIEW public.authenticated_news AS
SELECT
  item.id,
  source.name              AS source_name,
  source.homepage_url      AS source_homepage,
  item.title,
  item.permitted_excerpt   AS summary,
  item.canonical_url       AS url,
  item.published_at,
  item.observed_at         AS retrieved_at,
  item.language,
  item.geographic_scope    AS scope,
  item.country_code,
  item.is_fixture,
  item.source_status::text AS source_status
FROM public.content_items AS item
JOIN public.sources AS source ON source.id = item.source_id
WHERE item.content_kind = 'news_article'
  AND public.amanah_current_user_id() IS NOT NULL;
"""

# `security_barrier` on both admin views: the predicate is row-discriminating in
# the strongest sense — it removes every row for a non-administrator — so the
# planner must not push a cheap operator below it and evaluate against rows the
# predicate would have hidden.
_ADMIN_VIEWS = """
CREATE VIEW public.authenticated_collection_runs WITH (security_barrier = true) AS
SELECT
  run.id,
  run.source_id,
  source.source_key,
  source.name                AS source_name,
  run.source_seed_entry_id,
  run.idempotency_key,
  run.mode::text             AS mode,
  run.adapter_version,
  run.window_start,
  run.window_end,
  run.status::text           AS status,
  run.counts,
  run.coverage_warnings,
  run.safe_error_code,
  run.item_cap,
  run.attempt,
  run.max_attempts,
  run.next_run_at,
  run.is_dead_lettered,
  run.started_at,
  run.completed_at
FROM public.collection_runs AS run
JOIN public.sources AS source ON source.id = run.source_id
WHERE public.amanah_is_administrator();

-- `payload`, `checkpoint`, and `lease_owner` have no column here. A checkpoint
-- can hold provider cursors and a lease owner names a worker; an operator needs
-- the stage, the attempt, and the safe code, not the contents of the queue.
CREATE VIEW public.authenticated_background_jobs WITH (security_barrier = true) AS
SELECT
  job.id,
  job.collection_run_id,
  job.stage::text  AS stage,
  job.state::text  AS state,
  job.attempt,
  job.max_attempts,
  job.available_at,
  job.safe_error_code,
  job.is_dead_lettered,
  job.created_at,
  job.completed_at
FROM public.background_jobs AS job
WHERE public.amanah_is_administrator();
"""

_RUN_CHECKS = (
    ("attempt_non_negative", "attempt >= 0"),
    ("max_attempts_positive", "max_attempts > 0"),
    ("item_cap_positive", "item_cap IS NULL OR item_cap > 0"),
    ("lease_complete", "(lease_owner IS NULL) = (lease_expires_at IS NULL)"),
    ("running_requires_lease", "status <> 'running' OR lease_owner IS NOT NULL"),
    ("dead_letter_requires_failure", "NOT is_dead_lettered OR status = 'failed'"),
)

_RUN_COLUMNS = (
    "item_cap",
    "requested_by",
    "attempt",
    "max_attempts",
    "next_run_at",
    "lease_owner",
    "lease_expires_at",
    "is_dead_lettered",
)

_CONTENT_COLUMNS = (
    "normalized_context",
    "canonical_url_key",
    "headline_key",
    "dataset_annotations",
)


def enum_type(name: str) -> postgresql.ENUM:
    """Reference an enum type that already exists, without re-creating it."""
    return postgresql.ENUM(name=name, create_type=False, schema="public")


def _extend_collection_runs() -> None:
    op.add_column("collection_runs", sa.Column("item_cap", sa.Integer(), nullable=True))
    op.add_column("collection_runs", sa.Column("requested_by", sa.UUID(), nullable=True))
    op.add_column(
        "collection_runs",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "collection_runs",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
    )
    op.add_column(
        "collection_runs", sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("collection_runs", sa.Column("lease_owner", sa.String(length=200), nullable=True))
    op.add_column(
        "collection_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "collection_runs",
        sa.Column(
            "is_dead_lettered", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    for name, condition in _RUN_CHECKS:
        op.create_check_constraint(name, "collection_runs", condition, schema="public")
    op.create_index(
        "collection_runs_lease_expires_at_idx",
        "collection_runs",
        ["lease_expires_at"],
        postgresql_where=sa.text("status = 'running'"),
        schema="public",
    )


def _create_job_stage_type() -> None:
    """Create `job_stage`, unless an empty-database migration already did.

    `0001` builds its `CREATE TYPE` statements by iterating `ENUM_TYPES` at run
    time, so registering a new enum there makes that *historical* migration
    create it too. On a database migrated before this revision the type does not
    exist and must be created here; on one built from empty it already does.
    Both are true at once, so the statement is written to tolerate either.

    Registering the type in `ENUM_TYPES` is still correct: it is what maps the
    column and what makes `test_enum_types_match_the_controlled_vocabulary`
    check these labels against the published vocabulary.
    """
    labels = ", ".join(f"'{member.value}'" for member in JobStage)
    op.execute(
        "DO $$ BEGIN "
        f"CREATE TYPE public.job_stage AS ENUM ({labels}); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )


def _create_background_jobs() -> None:
    _create_job_stage_type()
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("collection_run_id", sa.UUID(), nullable=False),
        sa.Column("stage", enum_type("job_stage"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=300), nullable=False),
        sa.Column("state", enum_type("job_state"), server_default="queued", nullable=False),
        sa.Column("attempt", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lease_owner", sa.String(length=200), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "checkpoint", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "is_dead_lettered", sa.Boolean(), server_default=sa.text("false"), nullable=False
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["collection_run_id"],
            ["public.collection_runs.id"],
            name=op.f("background_jobs_collection_run_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("background_jobs_pkey")),
        sa.UniqueConstraint("idempotency_key", name=op.f("background_jobs_idempotency_key_unique")),
        sa.CheckConstraint("attempt >= 0", name=op.f("background_jobs_attempt_non_negative_check")),
        sa.CheckConstraint(
            "max_attempts > 0", name=op.f("background_jobs_max_attempts_positive_check")
        ),
        sa.CheckConstraint(
            "(lease_owner IS NULL) = (lease_expires_at IS NULL)",
            name=op.f("background_jobs_lease_complete_check"),
        ),
        sa.CheckConstraint(
            "state <> 'running' OR lease_owner IS NOT NULL",
            name=op.f("background_jobs_running_requires_lease_check"),
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'retry_wait') OR completed_at IS NOT NULL",
            name=op.f("background_jobs_terminal_requires_completion_check"),
        ),
        sa.CheckConstraint(
            "NOT is_dead_lettered OR state = 'failed'",
            name=op.f("background_jobs_dead_letter_requires_failure_check"),
        ),
        schema="public",
    )
    op.create_index(
        "background_jobs_state_available_at_idx",
        "background_jobs",
        ["state", "available_at"],
        postgresql_where=sa.text("state IN ('queued', 'retry_wait')"),
        schema="public",
    )
    op.create_index(
        "background_jobs_lease_expires_at_idx",
        "background_jobs",
        ["lease_expires_at"],
        postgresql_where=sa.text("state = 'running'"),
        schema="public",
    )
    op.create_index(
        "background_jobs_collection_run_id_stage_idx",
        "background_jobs",
        ["collection_run_id", "stage"],
        schema="public",
    )


def _extend_content_items() -> None:
    op.add_column(
        "content_items",
        sa.Column(
            "normalized_context",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("content_items", sa.Column("canonical_url_key", sa.Text(), nullable=True))
    op.add_column("content_items", sa.Column("headline_key", sa.Text(), nullable=True))
    op.add_column(
        "content_items",
        sa.Column(
            "dataset_annotations",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "language_format",
        "content_items",
        "language IS NULL OR language ~ '^[a-z]{2}$'",
        schema="public",
    )
    op.create_index(
        "content_items_canonical_url_key_idx",
        "content_items",
        ["canonical_url_key"],
        unique=True,
        postgresql_where=sa.text("canonical_url_key IS NOT NULL AND content_kind = 'news_article'"),
        schema="public",
    )
    op.create_index(
        "content_items_headline_key_idx",
        "content_items",
        ["headline_key"],
        unique=True,
        postgresql_where=sa.text("headline_key IS NOT NULL AND content_kind = 'news_article'"),
        schema="public",
    )
    op.add_column("sources", sa.Column("homepage_url", sa.Text(), nullable=True))


def _secure_background_jobs() -> None:
    """The same boundary every product table already has: deny, then name who may."""
    op.execute("ALTER TABLE public.background_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.background_jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY background_jobs_administrator_all ON public.background_jobs "
        "FOR ALL TO authenticated "
        "USING (public.amanah_is_administrator()) "
        "WITH CHECK (public.amanah_is_administrator())"
    )
    op.execute("REVOKE ALL ON public.background_jobs FROM anon, PUBLIC, authenticated")


def upgrade() -> None:
    _extend_collection_runs()
    _create_background_jobs()
    _extend_content_items()
    _secure_background_jobs()
    op.execute(_NEWS_VIEW)
    op.execute(_ADMIN_VIEWS)
    for view in NEW_VIEWS:
        op.execute(f"GRANT SELECT ON public.{view} TO authenticated")


def downgrade() -> None:
    for view in reversed(NEW_VIEWS):
        op.execute(f"DROP VIEW IF EXISTS public.{view}")

    op.drop_column("sources", "homepage_url", schema="public")
    op.drop_index("content_items_headline_key_idx", table_name="content_items", schema="public")
    op.drop_index(
        "content_items_canonical_url_key_idx", table_name="content_items", schema="public"
    )
    op.drop_constraint("content_items_language_format_check", "content_items", schema="public")
    for column in reversed(_CONTENT_COLUMNS):
        op.drop_column("content_items", column, schema="public")

    op.execute("DROP POLICY IF EXISTS background_jobs_administrator_all ON public.background_jobs")
    for index in (
        "background_jobs_collection_run_id_stage_idx",
        "background_jobs_lease_expires_at_idx",
        "background_jobs_state_available_at_idx",
    ):
        op.drop_index(index, table_name="background_jobs", schema="public")
    op.drop_table("background_jobs", schema="public")
    op.execute("DROP TYPE IF EXISTS public.job_stage")

    op.drop_index(
        "collection_runs_lease_expires_at_idx", table_name="collection_runs", schema="public"
    )
    for name, _condition in reversed(_RUN_CHECKS):
        op.drop_constraint(f"collection_runs_{name}_check", "collection_runs", schema="public")
    for column in reversed(_RUN_COLUMNS):
        op.drop_column("collection_runs", column, schema="public")
