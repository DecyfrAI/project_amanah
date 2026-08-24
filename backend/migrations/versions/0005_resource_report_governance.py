"""Add append-only governance audit records and Milestone 6 projections.

Resource lifecycle changes and report generation/downloads need durable audit
history.  The audit tables contain only safe catalog snapshots and opaque user,
report, request, and resource identifiers; no source text or author data enters
them.  Ready report immutability remains enforced by revision 0002.

Revision ID: 0005_resource_report_governance
Revises: 0004_collection_pipeline
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_resource_report_governance"
down_revision: str | None = "0004_collection_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MANAGED_RESOURCE_VIEW = """
CREATE OR REPLACE VIEW public.authenticated_managed_resources
WITH (security_barrier = true) AS
SELECT
  entry.id,
  entry.title,
  entry.organization,
  entry.url,
  entry.country_scope,
  entry.category::text AS category,
  entry.summary,
  entry.status::text AS status,
  entry.last_reviewed_at,
  entry.reviewed_by,
  entry.created_at,
  entry.updated_at
FROM public.resource_entries AS entry
WHERE public.amanah_is_reviewer();
"""

_RESOURCE_AUDIT_VIEW = """
CREATE OR REPLACE VIEW public.authenticated_resource_audit_events
WITH (security_barrier = true) AS
SELECT
  event.id,
  event.resource_entry_id,
  event.actor_user_id,
  event.action,
  event.snapshot,
  event.created_at
FROM public.resource_audit_events AS event
WHERE public.amanah_is_reviewer();
"""

_RESEARCH_REPORT_VIEW = """
CREATE OR REPLACE VIEW public.authenticated_research_reports
WITH (security_barrier = true) AS
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
  report.status::text AS status,
  report.safe_error_code,
  report.created_at,
  report.completed_at
FROM public.research_reports AS report
WHERE report.user_id = public.amanah_current_user_id()
   OR public.amanah_is_reviewer();
"""

_REPORT_AUDIT_VIEW = """
CREATE OR REPLACE VIEW public.authenticated_research_report_audit_events
WITH (security_barrier = true) AS
SELECT
  event.id,
  event.research_report_id,
  event.actor_user_id,
  event.action,
  event.request_id,
  event.created_at
FROM public.research_report_audit_events AS event
JOIN public.research_reports AS report ON report.id = event.research_report_id
WHERE report.user_id = public.amanah_current_user_id()
   OR public.amanah_is_reviewer();
"""


def _create_resource_audit_events() -> None:
    op.create_table(
        "resource_audit_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("resource_entry_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('created', 'updated', 'published', 'archived')",
            name=op.f("resource_audit_events_action_allowed_check"),
        ),
        sa.ForeignKeyConstraint(
            ["resource_entry_id"],
            ["public.resource_entries.id"],
            name=op.f("resource_audit_events_resource_entry_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("resource_audit_events_pkey")),
        schema="public",
    )
    op.create_index(
        "resource_audit_events_resource_entry_id_created_at_idx",
        "resource_audit_events",
        ["resource_entry_id", sa.literal_column("created_at DESC")],
        schema="public",
    )
    op.create_index(
        "resource_audit_events_actor_user_id_idx",
        "resource_audit_events",
        ["actor_user_id"],
        schema="public",
    )


def _create_report_audit_events() -> None:
    op.create_table(
        "research_report_audit_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("research_report_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('generated', 'downloaded')",
            name=op.f("research_report_audit_events_action_allowed_check"),
        ),
        sa.ForeignKeyConstraint(
            ["research_report_id"],
            ["public.research_reports.id"],
            name=op.f("research_report_audit_events_research_report_id_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("research_report_audit_events_pkey")),
        schema="public",
    )
    op.create_index(
        "research_report_audit_events_research_report_id_created_at_idx",
        "research_report_audit_events",
        ["research_report_id", sa.literal_column("created_at DESC")],
        schema="public",
    )
    op.create_index(
        "research_report_audit_events_actor_user_id_idx",
        "research_report_audit_events",
        ["actor_user_id"],
        schema="public",
    )


def _secure_audit_tables() -> None:
    for table in ("resource_audit_events", "research_report_audit_events"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON public.{table} FROM anon, PUBLIC, authenticated")

    op.execute(
        "CREATE POLICY resource_audit_events_reviewer_read "
        "ON public.resource_audit_events FOR SELECT TO authenticated "
        "USING (public.amanah_is_reviewer())"
    )
    op.execute(
        "CREATE POLICY resource_audit_events_reviewer_append "
        "ON public.resource_audit_events FOR INSERT TO authenticated "
        "WITH CHECK (public.amanah_is_reviewer() "
        "AND actor_user_id = public.amanah_current_user_id())"
    )
    op.execute(
        "CREATE POLICY research_report_audit_events_authorized_read "
        "ON public.research_report_audit_events FOR SELECT TO authenticated "
        "USING (public.amanah_is_reviewer() OR EXISTS ("
        "SELECT 1 FROM public.research_reports AS report "
        "WHERE report.id = research_report_id "
        "AND report.user_id = public.amanah_current_user_id()))"
    )
    op.execute(
        "CREATE POLICY research_report_audit_events_authorized_append "
        "ON public.research_report_audit_events FOR INSERT TO authenticated "
        "WITH CHECK (actor_user_id = public.amanah_current_user_id() AND ("
        "public.amanah_is_reviewer() OR EXISTS ("
        "SELECT 1 FROM public.research_reports AS report "
        "WHERE report.id = research_report_id "
        "AND report.user_id = public.amanah_current_user_id())))"
    )
    op.execute(
        "CREATE POLICY research_reports_reviewer_read ON public.research_reports "
        "FOR SELECT TO authenticated USING (public.amanah_is_reviewer())"
    )

    for table in ("resource_audit_events", "research_report_audit_events"):
        op.execute(
            f"CREATE TRIGGER {table}_append_only_trigger "
            f"BEFORE UPDATE OR DELETE ON public.{table} "
            "FOR EACH ROW EXECUTE FUNCTION public.amanah_reject_row_mutation()"
        )


def upgrade() -> None:
    _create_resource_audit_events()
    _create_report_audit_events()
    _secure_audit_tables()
    op.execute(_MANAGED_RESOURCE_VIEW)
    op.execute(_RESOURCE_AUDIT_VIEW)
    op.execute(_RESEARCH_REPORT_VIEW)
    op.execute(_REPORT_AUDIT_VIEW)
    for view in (
        "authenticated_managed_resources",
        "authenticated_resource_audit_events",
        "authenticated_research_report_audit_events",
    ):
        op.execute(f"GRANT SELECT ON public.{view} TO authenticated")


def downgrade() -> None:
    for view in (
        "authenticated_research_report_audit_events",
        "authenticated_resource_audit_events",
        "authenticated_managed_resources",
    ):
        op.execute(f"DROP VIEW IF EXISTS public.{view}")

    # Restore the owner-only projection from revision 0003.
    op.execute(
        _RESEARCH_REPORT_VIEW.replace(
            "WHERE report.user_id = public.amanah_current_user_id()\n"
            "   OR public.amanah_is_reviewer();",
            "WHERE report.user_id = public.amanah_current_user_id();",
        )
    )
    op.execute("DROP POLICY IF EXISTS research_reports_reviewer_read ON public.research_reports")
    for table in ("research_report_audit_events", "resource_audit_events"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only_trigger ON public.{table}")
    op.execute(
        "DROP POLICY IF EXISTS research_report_audit_events_authorized_append "
        "ON public.research_report_audit_events"
    )
    op.execute(
        "DROP POLICY IF EXISTS research_report_audit_events_authorized_read "
        "ON public.research_report_audit_events"
    )
    op.execute(
        "DROP POLICY IF EXISTS resource_audit_events_reviewer_append "
        "ON public.resource_audit_events"
    )
    op.execute(
        "DROP POLICY IF EXISTS resource_audit_events_reviewer_read ON public.resource_audit_events"
    )
    op.drop_index(
        "research_report_audit_events_actor_user_id_idx",
        table_name="research_report_audit_events",
        schema="public",
    )
    op.drop_index(
        "research_report_audit_events_research_report_id_created_at_idx",
        table_name="research_report_audit_events",
        schema="public",
    )
    op.drop_table("research_report_audit_events", schema="public")
    op.drop_index(
        "resource_audit_events_actor_user_id_idx",
        table_name="resource_audit_events",
        schema="public",
    )
    op.drop_index(
        "resource_audit_events_resource_entry_id_created_at_idx",
        table_name="resource_audit_events",
        schema="public",
    )
    op.drop_table("resource_audit_events", schema="public")
