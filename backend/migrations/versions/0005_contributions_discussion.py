"""Milestone 5: reviewer reads, FR-TOS-010 draft fields, and ADR 0004 discussion.

Three groups of change arrive here, and they are separate concerns that happen to
land in the same release.

*Reviewer visibility.* B-S17 gives reviewers a queue, and the `authenticated`
role has no privilege on any base table by design. `authenticated_review_tasks`
and `authenticated_review_events` are the projections that make the queue
readable, each carrying a reviewer predicate of its own so a routing mistake in
the API still cannot publish it. Neither has a column for the disputing user, so
a reviewer decides on the prediction rather than on who complained.

*FR-TOS-010.* `platform_policies` learns whether a platform runs a reporting form
or needs an email-style draft, and `prepared_platform_reports` learns what that
draft was addressed to. Constraints keep the two consistent: a form platform has
a form URL and no address, an email platform has an allow-listed address and a
subject. Nothing here sends anything.

*ADR 0004.* `snapshot_insights`, `discussion_posts`, `post_reactions`,
`dashboard_captures`, and `discussion_participants`. The decisions ADR 0004
records are enforced rather than documented: a post has a parent insight (foreign
key, `NOT NULL`), a snapshot cannot be edited after creation (trigger), a person
may react once per post (unique constraint), and retraction leaves the row while
dropping the body and the capture (check constraint, plus the API replacing the
body). There is no author-score column anywhere, which is what keeps "reactions
never rank authors" a property of the schema.

Revision ID: 0005_contributions_discussion
Revises: 0004_collection_pipeline
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from amanah.domain.enums import ReactionKind, ReportRecipientKind

revision: str = "0005_contributions_discussion"
down_revision: str | None = "0004_collection_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: New product tables. Each one gets row-level security enabled and forced, so a
#: table listed here without a policy denies everyone rather than defaulting open.
NEW_TABLES = (
    "discussion_participants",
    "dashboard_captures",
    "snapshot_insights",
    "discussion_posts",
    "post_reactions",
)

#: Projections added here, in creation order.
NEW_VIEWS = (
    "authenticated_review_tasks",
    "authenticated_review_events",
    "authenticated_snapshot_insights",
    "authenticated_dashboard_captures",
    "authenticated_discussion_posts",
    "authenticated_post_reactions",
    "authenticated_discussion_participation",
)

#: Migration `0001` builds its `CREATE TYPE` statements by iterating `ENUM_TYPES`
#: at run time, so registering a new enum there makes that historical migration
#: create it too. Guarding on `duplicate_object` is therefore correct for a
#: database built from empty *and* for one that was already migrated to `0004`.
_CREATE_ENUMS = """
DO $$
BEGIN
  CREATE TYPE public.report_recipient_kind AS ENUM ({recipients});
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE public.reaction_kind AS ENUM ({reactions});
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
""".format(
    recipients=", ".join(f"'{member.value}'" for member in ReportRecipientKind),
    reactions=", ".join(f"'{member.value}'" for member in ReactionKind),
)

# A snapshot exists so a later reader can check a claim against the numbers its
# author saw. A row that could be edited afterwards would not support that, so
# the immutability is a trigger rather than a convention. Deletion stays allowed:
# the tests truncate, and ADR 0004's "nothing is silently deleted" is about
# retracting a *note*, which keeps its row.
_IMMUTABILITY_TRIGGER = """
CREATE OR REPLACE FUNCTION public.amanah_refuse_update()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  RAISE EXCEPTION 'rows in % are immutable after creation', TG_TABLE_NAME
    USING ERRCODE = 'restrict_violation';
END $$;

CREATE TRIGGER snapshot_insights_immutable
BEFORE UPDATE ON public.snapshot_insights
FOR EACH ROW EXECUTE FUNCTION public.amanah_refuse_update();
"""

_REVIEW_VIEWS = """
-- The review queue behind /v1/review/tasks. Reviewer-only, and deliberately
-- silent about who disputed the prediction: a decision is about the model's
-- output, and knowing which user complained could only bias it.
CREATE VIEW public.authenticated_review_tasks WITH (security_barrier = true) AS
SELECT
  task.id,
  task.content_item_id,
  task.prediction_id,
  task.task_type::text   AS task_type,
  task.reason,
  task.priority,
  task.status::text      AS status,
  task.assigned_to,
  task.claim_expires_at,
  task.created_at,
  task.completed_at,
  item.title,
  item.permitted_excerpt,
  item.canonical_url,
  source.platform::text  AS platform,
  prediction.relevance::text      AS relevance,
  prediction.stance::text         AS stance,
  prediction.hate_types::text[]   AS hate_types,
  prediction.severity,
  prediction.score,
  prediction.confidence_tier::text AS confidence_tier,
  prediction.model_name,
  prediction.model_version
FROM public.review_tasks AS task
JOIN public.content_items AS item ON item.id = task.content_item_id
JOIN public.sources AS source ON source.id = item.source_id
JOIN public.predictions AS prediction ON prediction.id = task.prediction_id
WHERE public.amanah_is_reviewer();

-- Appended decisions, in the order they were made. `corrected_labels` is here
-- because a reviewer needs to see what a colleague corrected to; the training
-- quarantine flag is here because an operator needs to see that it was set and
-- that nothing consumed it.
CREATE VIEW public.authenticated_review_events WITH (security_barrier = true) AS
SELECT
  event.id,
  event.review_task_id,
  event.reviewer_id,
  event.decision::text AS decision,
  event.corrected_labels,
  event.note,
  event.is_training_candidate,
  event.created_at
FROM public.review_events AS event
WHERE public.amanah_is_reviewer();
"""

_DISCUSSION_VIEWS = """
-- A snapshot insight, readable by any verified reader. The author identifier is
-- projected because ADR 0004 makes authorship visible inside a thread; the
-- display name is joined from the profile so a reader sees a person rather than
-- a UUID, and there is no column anywhere that scores that person.
CREATE VIEW public.authenticated_snapshot_insights AS
SELECT
  insight.id,
  insight.user_id,
  profile.display_name AS author_display_name,
  insight.title,
  insight.claim,
  insight.metric,
  insight.numerator,
  insight.denominator,
  insight.window_start,
  insight.window_end,
  insight.figure_label,
  insight.filter_hash,
  insight.explorer_href,
  insight.source_keys,
  insight.items_observed,
  insight.items_relevant,
  insight.created_at
FROM public.snapshot_insights AS insight
LEFT JOIN public.user_profiles AS profile ON profile.user_id = insight.user_id
WHERE public.amanah_current_user_id() IS NOT NULL;

-- Captures are first-party renderings of Amanah figures, so any verified reader
-- may see one that is attached to a thread they can read.
CREATE VIEW public.authenticated_dashboard_captures AS
SELECT
  capture.id,
  capture.user_id,
  capture.alt_text,
  capture.image_source,
  capture.filter_hash,
  capture.explorer_href,
  capture.created_at
FROM public.dashboard_captures AS capture
WHERE public.amanah_current_user_id() IS NOT NULL;

-- Notes on an insight. A retracted note keeps its row and its position; the API
-- replaces the body, and the capture is already gone by constraint.
CREATE VIEW public.authenticated_discussion_posts AS
SELECT
  post.id,
  post.snapshot_insight_id,
  insight.title       AS insight_title,
  post.user_id,
  profile.display_name AS author_display_name,
  post.body,
  post.dashboard_capture_id,
  post.created_at,
  post.retracted_at
FROM public.discussion_posts AS post
JOIN public.snapshot_insights AS insight ON insight.id = post.snapshot_insight_id
LEFT JOIN public.user_profiles AS profile ON profile.user_id = post.user_id
WHERE public.amanah_current_user_id() IS NOT NULL;

-- Reaction counts per post, plus whichever reaction the *caller* left. There is
-- deliberately no per-author aggregate here and no way to build one from this
-- projection: `user_id` is filtered to the caller before it is exposed.
CREATE VIEW public.authenticated_post_reactions AS
SELECT
  post.id AS discussion_post_id,
  COUNT(*) FILTER (WHERE reaction.kind = 'useful')        AS useful_count,
  COUNT(*) FILTER (WHERE reaction.kind = 'needs_context') AS needs_context_count,
  MAX(reaction.kind::text) FILTER (
    WHERE reaction.user_id = public.amanah_current_user_id()
  ) AS viewer_reaction
FROM public.discussion_posts AS post
LEFT JOIN public.post_reactions AS reaction ON reaction.discussion_post_id = post.id
WHERE public.amanah_current_user_id() IS NOT NULL
GROUP BY post.id;

-- Whether the caller may take part. One row or none, and only ever about the
-- caller: an invitation list is not something a participant gets to read.
CREATE VIEW public.authenticated_discussion_participation
WITH (security_barrier = true) AS
SELECT
  participant.user_id,
  participant.granted_at
FROM public.discussion_participants AS participant
WHERE participant.user_id = public.amanah_current_user_id()
  AND participant.revoked_at IS NULL;
"""


def _extend_platform_policies() -> None:
    op.add_column(
        "platform_policies",
        sa.Column(
            "recipient_kind",
            postgresql.ENUM(name="report_recipient_kind", create_type=False),
            server_default="official_form",
            nullable=False,
        ),
        schema="public",
    )
    op.add_column("platform_policies", sa.Column("official_report_url", sa.Text(), nullable=True))
    op.add_column("platform_policies", sa.Column("report_email", sa.Text(), nullable=True))
    for name, condition in (
        (
            "official_report_url_https",
            "official_report_url IS NULL OR official_report_url LIKE 'https://%'",
        ),
        (
            "form_platform_has_report_url",
            "(recipient_kind = 'official_form') = (official_report_url IS NOT NULL)",
        ),
        (
            "email_platform_has_allowlisted_address",
            "(recipient_kind = 'allowlist_email') = (report_email IS NOT NULL)",
        ),
    ):
        op.create_check_constraint(name, "platform_policies", condition, schema="public")


def _extend_prepared_reports() -> None:
    op.add_column(
        "prepared_platform_reports",
        sa.Column(
            "recipient_kind",
            postgresql.ENUM(name="report_recipient_kind", create_type=False),
            server_default="official_form",
            nullable=False,
        ),
        schema="public",
    )
    op.add_column(
        "prepared_platform_reports", sa.Column("recipient_address", sa.Text(), nullable=True)
    )
    op.add_column("prepared_platform_reports", sa.Column("draft_subject", sa.Text(), nullable=True))
    op.create_check_constraint(
        "email_draft_has_recipient",
        "prepared_platform_reports",
        "(recipient_kind = 'allowlist_email') "
        "= (recipient_address IS NOT NULL AND draft_subject IS NOT NULL)",
        schema="public",
    )


def _create_discussion_participants() -> None:
    op.create_table(
        "discussion_participants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name="discussion_participants_revocation_after_grant_check",
        ),
        schema="public",
    )
    op.create_index(
        "discussion_participants_user_id_idx",
        "discussion_participants",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
        schema="public",
    )


def _create_dashboard_captures() -> None:
    op.create_table(
        "dashboard_captures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alt_text", sa.Text(), nullable=False),
        sa.Column("image_source", sa.Text(), nullable=False),
        sa.Column("filter_hash", sa.String(length=64), nullable=False),
        sa.Column("explorer_href", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "length(alt_text) BETWEEN 1 AND 300",
            name="dashboard_captures_alt_text_length_check",
        ),
        # `//host/path` starts with a slash and still leaves the site, so the
        # second slash is excluded as well as the scheme.
        sa.CheckConstraint(
            "explorer_href LIKE '/%' AND explorer_href NOT LIKE '//%'",
            name="dashboard_captures_explorer_href_is_relative_check",
        ),
        sa.CheckConstraint(
            "image_source LIKE '/%' AND image_source NOT LIKE '//%'",
            name="dashboard_captures_image_source_is_first_party_check",
        ),
        schema="public",
    )
    op.create_index(
        "dashboard_captures_user_id_created_at_idx",
        "dashboard_captures",
        ["user_id", sa.text("created_at DESC")],
        schema="public",
    )


def _create_snapshot_insights() -> None:
    op.create_table(
        "snapshot_insights",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("numerator", sa.Integer(), nullable=False),
        sa.Column("denominator", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("figure_label", sa.Text(), nullable=False),
        sa.Column("filter_hash", sa.String(length=64), nullable=False),
        sa.Column("explorer_href", sa.Text(), nullable=False),
        sa.Column(
            "source_keys",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("items_observed", sa.Integer(), nullable=False),
        sa.Column("items_relevant", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "numerator >= 0 AND denominator >= 0",
            name="snapshot_insights_counts_non_negative_check",
        ),
        sa.CheckConstraint(
            "numerator <= denominator",
            name="snapshot_insights_numerator_within_denominator_check",
        ),
        sa.CheckConstraint(
            "items_relevant >= 0 AND items_observed >= items_relevant",
            name="snapshot_insights_observed_covers_relevant_check",
        ),
        sa.CheckConstraint(
            "window_end >= window_start", name="snapshot_insights_window_ordered_check"
        ),
        sa.CheckConstraint(
            "length(claim) BETWEEN 1 AND 500", name="snapshot_insights_claim_length_check"
        ),
        sa.CheckConstraint(
            "length(title) BETWEEN 1 AND 200", name="snapshot_insights_title_length_check"
        ),
        sa.CheckConstraint(
            "explorer_href LIKE '/%' AND explorer_href NOT LIKE '//%'",
            name="snapshot_insights_explorer_href_is_relative_check",
        ),
        schema="public",
    )
    op.create_index(
        "snapshot_insights_created_at_idx",
        "snapshot_insights",
        [sa.text("created_at DESC")],
        schema="public",
    )
    op.create_index(
        "snapshot_insights_user_id_created_at_idx",
        "snapshot_insights",
        ["user_id", sa.text("created_at DESC")],
        schema="public",
    )


def _create_discussion_posts() -> None:
    op.create_table(
        "discussion_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("snapshot_insight_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("dashboard_capture_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("retracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["snapshot_insight_id"],
            ["public.snapshot_insights.id"],
            name="discussion_posts_snapshot_insight_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dashboard_capture_id"],
            ["public.dashboard_captures.id"],
            name="discussion_posts_dashboard_capture_id_fkey",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "length(body) BETWEEN 1 AND 4000", name="discussion_posts_body_length_check"
        ),
        sa.CheckConstraint(
            "retracted_at IS NULL OR dashboard_capture_id IS NULL",
            name="discussion_posts_retracted_post_has_no_capture_check",
        ),
        sa.CheckConstraint(
            "retracted_at IS NULL OR retracted_at >= created_at",
            name="discussion_posts_retraction_after_creation_check",
        ),
        schema="public",
    )
    op.create_index(
        "discussion_posts_snapshot_insight_id_created_at_idx",
        "discussion_posts",
        ["snapshot_insight_id", "created_at"],
        schema="public",
    )
    op.create_index(
        "discussion_posts_user_id_created_at_idx",
        "discussion_posts",
        ["user_id", sa.text("created_at DESC")],
        schema="public",
    )
    op.create_index(
        "discussion_posts_dashboard_capture_id_idx",
        "discussion_posts",
        ["dashboard_capture_id"],
        schema="public",
    )


def _create_post_reactions() -> None:
    op.create_table(
        "post_reactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("discussion_post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(name="reaction_kind", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["discussion_post_id"],
            ["public.discussion_posts.id"],
            name="post_reactions_discussion_post_id_fkey",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "discussion_post_id",
            "user_id",
            name="post_reactions_discussion_post_id_user_id_unique",
        ),
        schema="public",
    )
    op.create_index(
        "post_reactions_discussion_post_id_idx",
        "post_reactions",
        ["discussion_post_id"],
        schema="public",
    )
    op.create_index("post_reactions_user_id_idx", "post_reactions", ["user_id"], schema="public")


def _secure_new_tables() -> None:
    """Deny first, then name exactly who may reach what."""
    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON public.{table} FROM anon, PUBLIC, authenticated")

    # Invitations are issued by a reviewer or an administrator. A participant may
    # read their own row so the UI can say whether they may post; nobody reads
    # the list.
    op.execute(
        "CREATE POLICY discussion_participants_self_read ON public.discussion_participants "
        "FOR SELECT TO authenticated "
        "USING (user_id = public.amanah_current_user_id() OR public.amanah_is_reviewer())"
    )
    op.execute(
        "CREATE POLICY discussion_participants_reviewer_write "
        "ON public.discussion_participants "
        "FOR ALL TO authenticated "
        "USING (public.amanah_is_reviewer()) "
        "WITH CHECK (public.amanah_is_reviewer())"
    )

    # Insights, posts, and captures are read by any verified reader and written
    # only by their own author. Editing is not granted at all: a snapshot is
    # immutable, and a retraction is performed by the service, not by a client
    # UPDATE.
    for table in ("snapshot_insights", "dashboard_captures", "discussion_posts"):
        op.execute(
            f"CREATE POLICY {table}_authenticated_read ON public.{table} "
            "FOR SELECT TO authenticated "
            "USING (public.amanah_current_user_id() IS NOT NULL)"
        )
        op.execute(
            f"CREATE POLICY {table}_author_insert ON public.{table} "
            "FOR INSERT TO authenticated "
            "WITH CHECK (user_id = public.amanah_current_user_id())"
        )
    op.execute(
        "CREATE POLICY discussion_posts_author_update ON public.discussion_posts "
        "FOR UPDATE TO authenticated "
        "USING (user_id = public.amanah_current_user_id()) "
        "WITH CHECK (user_id = public.amanah_current_user_id())"
    )

    # A reaction is the caller's own or it is not theirs to write. Counts are
    # read through the aggregate projection, which never exposes another
    # person's row.
    op.execute(
        "CREATE POLICY post_reactions_authenticated_read ON public.post_reactions "
        "FOR SELECT TO authenticated "
        "USING (public.amanah_current_user_id() IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY post_reactions_owner_write ON public.post_reactions "
        "FOR ALL TO authenticated "
        "USING (user_id = public.amanah_current_user_id()) "
        "WITH CHECK (user_id = public.amanah_current_user_id())"
    )


def upgrade() -> None:
    op.execute(_CREATE_ENUMS)
    _extend_platform_policies()
    _extend_prepared_reports()
    _create_discussion_participants()
    _create_dashboard_captures()
    _create_snapshot_insights()
    _create_discussion_posts()
    _create_post_reactions()
    op.execute(_IMMUTABILITY_TRIGGER)
    _secure_new_tables()
    op.execute(_REVIEW_VIEWS)
    op.execute(_DISCUSSION_VIEWS)
    # The prepared-report projection gains the three FR-TOS-010 columns. Replacing
    # rather than dropping keeps the grant and any dependent object intact;
    # Postgres allows appending columns to a view this way.
    op.execute(PREPARED_REPORTS_VIEW_WITH_DRAFT)
    for view in NEW_VIEWS:
        op.execute(f"GRANT SELECT ON public.{view} TO authenticated")


#: The owner-scoped prepared-report projection, before and after FR-TOS-010.
#: Two literal definitions rather than one interpolated builder: there are
#: exactly two, `CREATE OR REPLACE` needs the whole body either way, and building
#: SQL by string interpolation is a habit worth not having in a migration.
_PREPARED_REPORTS_VIEW_HEAD = """
CREATE OR REPLACE VIEW public.authenticated_prepared_platform_reports
WITH (security_barrier = true) AS
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
  report.updated_at"""

_PREPARED_REPORTS_VIEW_TAIL = """
FROM public.prepared_platform_reports AS report
WHERE report.user_id = public.amanah_current_user_id();
"""

PREPARED_REPORTS_VIEW_WITH_DRAFT = (
    _PREPARED_REPORTS_VIEW_HEAD
    + """,
  report.recipient_kind::text AS recipient_kind,
  report.recipient_address,
  report.draft_subject"""
    + _PREPARED_REPORTS_VIEW_TAIL
)

PREPARED_REPORTS_VIEW_WITHOUT_DRAFT = _PREPARED_REPORTS_VIEW_HEAD + _PREPARED_REPORTS_VIEW_TAIL


def downgrade() -> None:
    for view in reversed(NEW_VIEWS):
        op.execute(f"DROP VIEW IF EXISTS public.{view}")
    # Columns cannot be dropped from a view in place, so the projection is
    # rebuilt from scratch before the columns behind it go away.
    op.execute("DROP VIEW IF EXISTS public.authenticated_prepared_platform_reports")
    op.execute(PREPARED_REPORTS_VIEW_WITHOUT_DRAFT)
    op.execute("GRANT SELECT ON public.authenticated_prepared_platform_reports TO authenticated")

    op.execute("DROP TRIGGER IF EXISTS snapshot_insights_immutable ON public.snapshot_insights")
    op.execute("DROP FUNCTION IF EXISTS public.amanah_refuse_update()")

    for table in reversed(NEW_TABLES):
        op.drop_table(table, schema="public")
    op.execute("DROP TYPE IF EXISTS public.reaction_kind")

    op.drop_constraint(
        "prepared_platform_reports_email_draft_has_recipient_check",
        "prepared_platform_reports",
        schema="public",
    )
    for column in ("draft_subject", "recipient_address", "recipient_kind"):
        op.drop_column("prepared_platform_reports", column, schema="public")

    for name in (
        "email_platform_has_allowlisted_address",
        "form_platform_has_report_url",
        "official_report_url_https",
    ):
        op.drop_constraint(f"platform_policies_{name}_check", "platform_policies", schema="public")
    for column in ("report_email", "official_report_url", "recipient_kind"):
        op.drop_column("platform_policies", column, schema="public")
    op.execute("DROP TYPE IF EXISTS public.report_recipient_kind")
