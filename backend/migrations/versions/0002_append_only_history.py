"""Make decision history append-only and ready report snapshots immutable.

`spec.md` section 14.6 requires review and contribution events to be append-only
and a report snapshot to be immutable once it is `ready`. Predictions are the
same kind of record: a reviewer correction appends a review event, it never
rewrites what the model produced.

Enforcing this with triggers rather than with repository discipline means the
guarantee survives a future repository, a background job, an admin session, and
anything else that can reach the table.

Revision ID: 0002_append_only_history
Revises: 0001_core_schema
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_append_only_history"
down_revision: str | None = "0001_core_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Tables whose rows are history: written once, never updated, never deleted.
APPEND_ONLY_TABLES = ("predictions", "review_events", "contribution_events")

_REJECT_MUTATION_FUNCTION = """
CREATE OR REPLACE FUNCTION public.amanah_reject_row_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  RAISE EXCEPTION
    'append_only_violation: % rows cannot be updated or deleted', TG_TABLE_NAME
    USING ERRCODE = 'restrict_violation';
END;
$$;
"""

#: A pending or failed snapshot may still be completed or retried. Once it is
#: `ready` it is frozen, and regenerating means a new row under a new identifier.
_REJECT_READY_REPORT_FUNCTION = """
CREATE OR REPLACE FUNCTION public.amanah_reject_ready_report_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF OLD.status = 'ready' THEN
    RAISE EXCEPTION
      'immutable_snapshot_violation: a ready research report cannot be changed'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
END;
$$;
"""


def upgrade() -> None:
    op.execute(_REJECT_MUTATION_FUNCTION)
    op.execute(_REJECT_READY_REPORT_FUNCTION)

    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only_trigger "
            f"BEFORE UPDATE OR DELETE ON public.{table} "
            "FOR EACH ROW EXECUTE FUNCTION public.amanah_reject_row_mutation()"
        )

    op.execute(
        "CREATE TRIGGER research_reports_ready_immutable_trigger "
        "BEFORE UPDATE OR DELETE ON public.research_reports "
        "FOR EACH ROW EXECUTE FUNCTION public.amanah_reject_ready_report_change()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS research_reports_ready_immutable_trigger ON public.research_reports"
    )
    for table in reversed(APPEND_ONLY_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only_trigger ON public.{table}")
    op.execute("DROP FUNCTION IF EXISTS public.amanah_reject_ready_report_change()")
    op.execute("DROP FUNCTION IF EXISTS public.amanah_reject_row_mutation()")
