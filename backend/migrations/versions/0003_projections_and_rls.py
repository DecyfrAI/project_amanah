"""Authenticated-safe projections and the row-level-security boundary.

Two boundaries are created here and they are deliberately different in kind.

*Column* safety comes from the `authenticated_*` views. They are the only
relations `authenticated` may read, and they simply have no column for encrypted
text, normalized model input, private storage keys, provider payloads, opaque
source item identifiers, or author identifiers. A field that does not exist in
the projection cannot be leaked by a later endpoint that returns "everything".

*Row* safety comes from row-level security on the base tables, plus the owner and
role predicates the views carry. Anonymous callers reach neither: every privilege
is revoked from `anon` and from `PUBLIC` on every table, view, sequence, and
function, no policy names `anon`, and each view additionally refuses to return a
row when no verified identity is present on the session.

Identity comes from `request.jwt.claims`, the session setting Supabase's
PostgREST populates from a verified access token. This service sets the same
setting on its own connection for each request, so the API's queries are scoped
by exactly the predicate a direct Supabase client would face.

Revision ID: 0003_projections_and_rls
Revises: 0002_append_only_history
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_projections_and_rls"
down_revision: str | None = "0002_append_only_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Every product table. Row-level security is enabled and forced on all of them,
#: so a table added to this list without a policy denies everyone rather than
#: defaulting open.
PRODUCT_TABLES = (
    "sources",
    "source_seed_entries",
    "dataset_packages",
    "dataset_import_runs",
    "collection_runs",
    "content_items",
    "predictions",
    "review_tasks",
    "review_events",
    "metric_buckets",
    "news_event_links",
    "insight_snapshots",
    "user_profiles",
    "content_submissions",
    "classification_disputes",
    "contribution_events",
    "platform_policies",
    "policy_matches",
    "prepared_platform_reports",
    "resource_entries",
    "research_reports",
)

#: Readable by any verified base-role user through the projections below.
SHARED_READ_TABLES = (
    "sources",
    "content_items",
    "predictions",
    "metric_buckets",
    "news_event_links",
    "insight_snapshots",
    "dataset_packages",
    "policy_matches",
)

#: Readable only by the user named in the row's `user_id`. Reviewers reach these
#: records through the review queue, never through an owner-scoped read, so no
#: role bypasses the predicate.
OWNER_SCOPED_TABLES = (
    "user_profiles",
    "content_submissions",
    "classification_disputes",
    "contribution_events",
    "prepared_platform_reports",
    "research_reports",
)

#: Curated catalogues: published entries reach everyone, drafts reach reviewers.
PUBLISHED_CATALOGUE_TABLES = ("resource_entries", "platform_policies")

#: Operational configuration and run history: administrators only.
ADMINISTRATOR_TABLES = (
    "source_seed_entries",
    "dataset_import_runs",
    "collection_runs",
)

#: The authenticated-safe projections, in creation order.
AUTHENTICATED_VIEWS = (
    "authenticated_items",
    "authenticated_metric_buckets",
    "authenticated_source_status",
    "authenticated_resources",
    "authenticated_user_profile",
    "authenticated_content_submissions",
    "authenticated_classification_disputes",
    "authenticated_contribution_events",
    "authenticated_prepared_platform_reports",
    "authenticated_research_reports",
)

_IDENTITY_FUNCTIONS = """
-- The verified subject of the current request, or NULL when there is none.
-- Reads the same session setting PostgREST populates from a validated access
-- token, so one predicate covers the API's own connection and a direct Supabase
-- client alike.
CREATE OR REPLACE FUNCTION public.amanah_current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public
AS $$
  SELECT NULLIF(
    COALESCE(
      NULLIF(current_setting('request.jwt.claim.sub', true), ''),
      NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
    ),
    ''
  )::uuid
$$;

-- The product role carried by the verified token, or NULL when absent. Supabase
-- puts the product role in `app_metadata`; the top-level `role` claim is always
-- the Postgres role and is deliberately ignored here.
CREATE OR REPLACE FUNCTION public.amanah_current_role()
RETURNS text
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public
AS $$
  SELECT NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
         -> 'app_metadata' ->> 'role'
$$;

CREATE OR REPLACE FUNCTION public.amanah_is_reviewer()
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public
AS $$
  SELECT public.amanah_current_user_id() IS NOT NULL
     AND public.amanah_current_role() IN ('reviewer', 'administrator')
$$;

CREATE OR REPLACE FUNCTION public.amanah_is_administrator()
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = pg_catalog, public
AS $$
  SELECT public.amanah_current_user_id() IS NOT NULL
     AND public.amanah_current_role() = 'administrator'
$$;
"""

IDENTITY_FUNCTION_NAMES = (
    "amanah_current_user_id()",
    "amanah_current_role()",
    "amanah_is_reviewer()",
    "amanah_is_administrator()",
)

# `security_barrier` stops a cheap operator from being pushed below a view's own
# predicate and observing values from rows that predicate would have removed. It
# is applied to every view whose predicate is *row-discriminating* — the
# owner-scoped views and the published-only catalogue — because those are the
# ones with rows to hide.
#
# The shared projections below carry it deliberately *not*. Their only predicate
# is "a verified identity exists", which is the same answer for every row, so a
# barrier would hide nothing while blocking the planner from using the ordering
# index for the item list's sort — the index that makes cursor pagination cheap.
_VIEWS = """
-- Item projection behind /v1/items, /v1/items/{id}, /v1/news, and the dashboard
-- headline list. `source_item_id`, `text_ciphertext`, `normalized_text`,
-- `raw_object_key`, `metadata`, `content_hash`, and `submitted_origin` have no
-- column here, so no reader can reach raw content or an author identifier.
CREATE VIEW public.authenticated_items AS
SELECT
  item.id,
  item.content_kind::text,
  source.platform::text               AS platform,
  source.kind::text                   AS source_kind,
  source.name                     AS source_name,
  item.title,
  item.permitted_excerpt,
  item.publisher_or_container,
  item.canonical_url,
  item.published_at,
  item.observed_at,
  item.language,
  item.country_code,
  item.geographic_scope,
  item.source_status::text            AS source_status,
  item.is_fixture,
  item.effective_review_state::text   AS review_state,
  package.provider                 AS dataset_provider,
  package.name                     AS dataset_name,
  package.version                  AS dataset_version,
  package.license_id               AS dataset_license_id,
  package.landing_page_url         AS dataset_landing_page_url,
  latest.id                        AS prediction_id,
  latest.relevance::text              AS relevance,
  latest.stance::text                 AS stance,
  -- Cast to `text[]`: a client that does not know the `hate_type` enum type
  -- would otherwise receive the array as an undecoded literal string.
  latest.hate_types::text[]           AS hate_types,
  latest.severity,
  latest.narrative_tags,
  latest.score,
  latest.confidence_tier::text        AS confidence_tier,
  latest.requires_review,
  latest.rationale,
  latest.model_name,
  latest.model_version,
  latest.prompt_version,
  latest.taxonomy_version,
  latest.inferred_at
FROM public.content_items AS item
JOIN public.sources AS source ON source.id = item.source_id
LEFT JOIN public.dataset_packages AS package ON package.id = item.dataset_package_id
LEFT JOIN LATERAL (
  -- The current prediction is the newest successful one. Superseded executions
  -- stay in `predictions` as history rather than being overwritten.
  SELECT
    prediction.id, prediction.relevance, prediction.stance, prediction.hate_types,
    prediction.severity, prediction.narrative_tags, prediction.score,
    prediction.confidence_tier, prediction.requires_review, prediction.rationale,
    prediction.model_name, prediction.model_version, prediction.prompt_version,
    prediction.taxonomy_version, prediction.inferred_at
  FROM public.predictions AS prediction
  WHERE prediction.content_item_id = item.id
    AND prediction.inference_status = 'succeeded'
  ORDER BY prediction.created_at DESC, prediction.id DESC
  LIMIT 1
) AS latest ON TRUE
WHERE public.amanah_current_user_id() IS NOT NULL;

-- Deterministic aggregates. Counts rather than a rate: the numerator and the
-- denominator are read together so a rate is never published bare.
CREATE VIEW public.authenticated_metric_buckets AS
SELECT
  bucket.id,
  bucket.metric_key,
  bucket.source_id,
  source.name          AS source_name,
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

-- Connector state for /v1/connections. No key, connection string, host, or
-- provider error body has a column here.
CREATE VIEW public.authenticated_source_status AS
SELECT
  source.id,
  source.source_key,
  source.name,
  source.kind::text     AS kind,
  source.platform::text AS platform,
  source.purpose,
  source.policy_url,
  source.is_enabled,
  source.status::text   AS status,
  source.last_success_at,
  source.last_checked_at,
  source.safe_warning
FROM public.sources AS source
WHERE public.amanah_current_user_id() IS NOT NULL;

-- Only reviewed, published entries. Draft and archived rows never appear, so an
-- unreviewed description cannot be served as curation.
CREATE VIEW public.authenticated_resources WITH (security_barrier = true) AS
SELECT
  entry.id,
  entry.title,
  entry.organization,
  entry.url,
  entry.country_scope,
  entry.category::text  AS category,
  entry.summary,
  entry.last_reviewed_at
FROM public.resource_entries AS entry
WHERE entry.status = 'published'
  AND public.amanah_current_user_id() IS NOT NULL;

CREATE VIEW public.authenticated_user_profile WITH (security_barrier = true) AS
SELECT
  profile.user_id,
  profile.display_name,
  profile.role::text              AS role,
  profile.onboarding_status::text AS onboarding_status,
  profile.content_safety_preferences,
  profile.created_at,
  profile.updated_at
FROM public.user_profiles AS profile
WHERE profile.user_id = public.amanah_current_user_id();

CREATE VIEW public.authenticated_content_submissions WITH (security_barrier = true) AS
SELECT
  submission.id,
  submission.user_id,
  submission.submitted_url,
  submission.canonical_url,
  submission.content_item_id,
  submission.status::text AS status,
  submission.safe_error_code,
  submission.submitted_at,
  submission.processed_at
FROM public.content_submissions AS submission
WHERE submission.user_id = public.amanah_current_user_id();

CREATE VIEW public.authenticated_classification_disputes WITH (security_barrier = true) AS
SELECT
  dispute.id,
  dispute.user_id,
  dispute.content_item_id,
  dispute.prediction_id,
  dispute.reason,
  dispute.status::text    AS status,
  dispute.resolution_summary,
  dispute.created_at,
  dispute.resolved_at
FROM public.classification_disputes AS dispute
WHERE dispute.user_id = public.amanah_current_user_id();

CREATE VIEW public.authenticated_contribution_events WITH (security_barrier = true) AS
SELECT
  event.id,
  event.user_id,
  event.contribution_type::text AS contribution_type,
  event.contribution_id,
  event.event_type::text        AS event_type,
  event.public_message,
  event.created_at
FROM public.contribution_events AS event
WHERE event.user_id = public.amanah_current_user_id();

CREATE VIEW public.authenticated_prepared_platform_reports WITH (security_barrier = true) AS
SELECT
  report.id,
  report.user_id,
  report.content_item_id,
  report.platform,
  report.platform_policy_id,
  report.policy_version,
  report.evidence_summary,
  report.suggested_text,
  report.status::text  AS status,
  report.submitted_at,
  report.outcome::text AS outcome,
  report.outcome_note,
  report.created_at,
  report.updated_at
FROM public.prepared_platform_reports AS report
WHERE report.user_id = public.amanah_current_user_id();

CREATE VIEW public.authenticated_research_reports WITH (security_barrier = true) AS
SELECT
  report.id,
  report.user_id,
  report.filter_hash,
  report.filters,
  report.data_version,
  report.coverage_snapshot,
  report.sections,
  report.citation_ids,
  report.methodology_version,
  report.redaction_mode::text AS redaction_mode,
  report.status::text         AS status,
  report.safe_error_code,
  report.created_at,
  report.completed_at
FROM public.research_reports AS report
WHERE report.user_id = public.amanah_current_user_id();
"""


def _enable_row_level_security() -> None:
    for table in PRODUCT_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        # FORCE so the table owner is subject to its own policies too, rather
        # than quietly exempt.
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")


def _create_policies() -> None:
    for table in SHARED_READ_TABLES:
        op.execute(
            f"CREATE POLICY {table}_authenticated_read ON public.{table} "
            "FOR SELECT TO authenticated "
            "USING (public.amanah_current_user_id() IS NOT NULL)"
        )

    for table in PUBLISHED_CATALOGUE_TABLES:
        op.execute(
            f"CREATE POLICY {table}_authenticated_read ON public.{table} "
            "FOR SELECT TO authenticated "
            "USING (public.amanah_current_user_id() IS NOT NULL "
            "AND (status = 'published' OR public.amanah_is_reviewer()))"
        )
        op.execute(
            f"CREATE POLICY {table}_reviewer_write ON public.{table} "
            "FOR ALL TO authenticated "
            "USING (public.amanah_is_reviewer()) "
            "WITH CHECK (public.amanah_is_reviewer())"
        )

    for table in OWNER_SCOPED_TABLES:
        op.execute(
            f"CREATE POLICY {table}_owner_read ON public.{table} "
            "FOR SELECT TO authenticated "
            "USING (user_id = public.amanah_current_user_id())"
        )
        op.execute(
            f"CREATE POLICY {table}_owner_insert ON public.{table} "
            "FOR INSERT TO authenticated "
            "WITH CHECK (user_id = public.amanah_current_user_id())"
        )
        op.execute(
            f"CREATE POLICY {table}_owner_update ON public.{table} "
            "FOR UPDATE TO authenticated "
            "USING (user_id = public.amanah_current_user_id()) "
            "WITH CHECK (user_id = public.amanah_current_user_id())"
        )

    for table in ADMINISTRATOR_TABLES:
        op.execute(
            f"CREATE POLICY {table}_administrator_all ON public.{table} "
            "FOR ALL TO authenticated "
            "USING (public.amanah_is_administrator()) "
            "WITH CHECK (public.amanah_is_administrator())"
        )

    # Administrators also maintain the source catalogue and dataset manifests,
    # which base-role users only read.
    for table in ("sources", "dataset_packages"):
        op.execute(
            f"CREATE POLICY {table}_administrator_write ON public.{table} "
            "FOR ALL TO authenticated "
            "USING (public.amanah_is_administrator()) "
            "WITH CHECK (public.amanah_is_administrator())"
        )

    # The review queue is reviewer-only, and a reviewer may only append a
    # decision under their own identity.
    op.execute(
        "CREATE POLICY review_tasks_reviewer_all ON public.review_tasks "
        "FOR ALL TO authenticated "
        "USING (public.amanah_is_reviewer()) "
        "WITH CHECK (public.amanah_is_reviewer())"
    )
    op.execute(
        "CREATE POLICY review_events_reviewer_read ON public.review_events "
        "FOR SELECT TO authenticated "
        "USING (public.amanah_is_reviewer())"
    )
    op.execute(
        "CREATE POLICY review_events_reviewer_append ON public.review_events "
        "FOR INSERT TO authenticated "
        "WITH CHECK (public.amanah_is_reviewer() "
        "AND reviewer_id = public.amanah_current_user_id())"
    )


def _apply_grants() -> None:
    # Deny first. `anon` and `PUBLIC` lose every privilege on everything that
    # exists now and on anything created later in this schema.
    op.execute("REVOKE ALL ON SCHEMA public FROM anon")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, PUBLIC")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, PUBLIC")
    op.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, PUBLIC")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, PUBLIC")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, PUBLIC"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, PUBLIC"
    )

    # Base tables stay ungranted for `authenticated` as well: the projections are
    # the only relations it may read, which is what makes column safety
    # structural rather than a matter of writing careful queries.
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated")
    op.execute("GRANT USAGE ON SCHEMA public TO authenticated")
    for view in AUTHENTICATED_VIEWS:
        op.execute(f"GRANT SELECT ON public.{view} TO authenticated")
    for function in IDENTITY_FUNCTION_NAMES:
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{function} TO authenticated")


def upgrade() -> None:
    op.execute(_IDENTITY_FUNCTIONS)
    op.execute(_VIEWS)
    _enable_row_level_security()
    _create_policies()
    _apply_grants()


def _drop_policies() -> None:
    for table in SHARED_READ_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_authenticated_read ON public.{table}")
    for table in PUBLISHED_CATALOGUE_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_authenticated_read ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_reviewer_write ON public.{table}")
    for table in OWNER_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_read ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_insert ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_update ON public.{table}")
    for table in ADMINISTRATOR_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_administrator_all ON public.{table}")
    for table in ("sources", "dataset_packages"):
        op.execute(f"DROP POLICY IF EXISTS {table}_administrator_write ON public.{table}")
    op.execute("DROP POLICY IF EXISTS review_tasks_reviewer_all ON public.review_tasks")
    op.execute("DROP POLICY IF EXISTS review_events_reviewer_read ON public.review_events")
    op.execute("DROP POLICY IF EXISTS review_events_reviewer_append ON public.review_events")


def downgrade() -> None:
    for view in reversed(AUTHENTICATED_VIEWS):
        op.execute(f"DROP VIEW IF EXISTS public.{view}")
    _drop_policies()
    for table in PRODUCT_TABLES:
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
    for function in reversed(IDENTITY_FUNCTION_NAMES):
        op.execute(f"DROP FUNCTION IF EXISTS public.{function}")
