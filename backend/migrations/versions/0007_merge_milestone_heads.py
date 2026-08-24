"""Rejoin the three revision branches that grew out of `0004`.

Milestones 4, 5, and 6 each added a revision whose parent is
`0004_collection_pipeline`, so the history branched into three heads:
`0005_analysis_and_image_corpus`, `0005_resource_report_governance`, and
`0006_policy_channel_checks` (via `0005_contributions_discussion`).

Three heads is not a cosmetic untidiness. `alembic upgrade head` refuses to
choose between them, so applying migrations to any *fresh* database fails —
which is exactly what a new deployment and the disposable-database test suite
both do. The branches themselves are independent: they touch different tables
and never ran in a conflicting order against the existing database, so nothing
here needs reordering.

This revision therefore carries no DDL. It is graph bookkeeping: it names all
three heads as parents so `head` resolves to one revision again. There is no
downgrade body for the same reason — reversing a merge means returning to three
heads, which Alembic does by walking back past this node.

Revision ID: 0007_merge_milestone_heads
Revises: 0005_analysis_and_image_corpus, 0005_resource_report_governance, 0006_policy_channel_checks
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0007_merge_milestone_heads"
down_revision: str | Sequence[str] | None = (
    "0005_analysis_and_image_corpus",
    "0005_resource_report_governance",
    "0006_policy_channel_checks",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema change: this revision only rejoins the history."""


def downgrade() -> None:
    """No schema change to reverse."""
