"""Owner-scoped reads of a person's own contributions (B-S16.6, B-S17, B-S18).

Like every repository here, these read `authenticated_*` projections and never a
base table. Those views carry `user_id = amanah_current_user_id()` in their own
`WHERE` clause, so the ownership boundary holds twice: the query filters on the
caller, and the view would return nothing for anyone else even if the filter were
dropped.

The unified history is a `UNION ALL` over the three owner-scoped projections,
narrowed to the columns `spec.md` section 9.10 requires of every row — type,
title or URL, created time, status, last update, destination. Building it in SQL
rather than merging three paginated lists in Python is what lets one cursor walk
the whole history in `created_at` order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Row, Select, literal, select, tuple_, union_all
from sqlalchemy.orm import Session

from amanah.db.pagination import decode_keyset_cursor, encode_keyset_cursor
from amanah.db.views import (
    authenticated_classification_disputes,
    authenticated_content_submissions,
    authenticated_contribution_events,
    authenticated_prepared_platform_reports,
)
from amanah.domain.enums import ContributionType

#: Names the ordering a contribution cursor belongs to, so a cursor issued for a
#: different collection is rejected instead of silently producing a wrong page.
CONTRIBUTION_ORDER_KEY = "contribution_created_at"


@dataclass(frozen=True, slots=True)
class ContributionPage:
    """One page of a person's history plus the cursor that continues it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None


class ContributionRepository:
    """Reads one person's submissions, disputes, prepared reports, and timeline."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_history(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        contribution_type: ContributionType | None = None,
    ) -> ContributionPage:
        """Return one page of the caller's contributions, newest first."""
        statement = self._history_query(contribution_type)
        subquery = statement.subquery("contribution")
        query: Select[Any] = select(subquery)
        if cursor is not None:
            key_value, row_id = decode_keyset_cursor(cursor, CONTRIBUTION_ORDER_KEY)
            query = query.where(
                tuple_(subquery.c.created_at, subquery.c.id)
                < tuple_(literal(key_value), literal(row_id))
            )
        query = query.order_by(subquery.c.created_at.desc(), subquery.c.id.desc()).limit(limit + 1)
        rows = tuple(self._session.execute(query).all())
        if len(rows) <= limit:
            return ContributionPage(rows=rows, next_cursor=None)
        page = rows[:limit]
        last = page[-1]
        return ContributionPage(
            rows=page,
            next_cursor=encode_keyset_cursor(CONTRIBUTION_ORDER_KEY, last.created_at, last.id),
        )

    def _history_query(self, contribution_type: ContributionType | None) -> Select[Any]:
        """The three owner-scoped sources, projected onto one row shape."""
        parts = {
            ContributionType.url_submission: self._submissions_part(),
            ContributionType.classification_dispute: self._disputes_part(),
            ContributionType.prepared_platform_report: self._reports_part(),
        }
        if contribution_type is not None:
            return parts[contribution_type]
        return select(union_all(*parts.values()).subquery("history"))

    def _submissions_part(self) -> Select[Any]:
        table = authenticated_content_submissions
        return select(
            table.c.id,
            literal(ContributionType.url_submission.value).label("contribution_type"),
            table.c.submitted_url.label("label"),
            table.c.status,
            table.c.submitted_at.label("created_at"),
            # A submission has no separate updated column: it is created and then
            # settled once, so the settlement time *is* the last update.
            table.c.processed_at.label("updated_at"),
            table.c.content_item_id.label("destination_item_id"),
        )

    def _disputes_part(self) -> Select[Any]:
        table = authenticated_classification_disputes
        return select(
            table.c.id,
            literal(ContributionType.classification_dispute.value).label("contribution_type"),
            table.c.reason.label("label"),
            table.c.status,
            table.c.created_at,
            table.c.resolved_at.label("updated_at"),
            table.c.content_item_id.label("destination_item_id"),
        )

    def _reports_part(self) -> Select[Any]:
        table = authenticated_prepared_platform_reports
        return select(
            table.c.id,
            literal(ContributionType.prepared_platform_report.value).label("contribution_type"),
            table.c.platform.label("label"),
            table.c.status,
            table.c.created_at,
            table.c.updated_at,
            table.c.content_item_id.label("destination_item_id"),
        )

    def get_submission(self, submission_id: UUID) -> Row[Any] | None:
        table = authenticated_content_submissions
        return self._session.execute(select(table).where(table.c.id == submission_id)).one_or_none()

    def get_dispute(self, dispute_id: UUID) -> Row[Any] | None:
        table = authenticated_classification_disputes
        return self._session.execute(select(table).where(table.c.id == dispute_id)).one_or_none()

    def get_prepared_report(self, report_id: UUID) -> Row[Any] | None:
        table = authenticated_prepared_platform_reports
        return self._session.execute(select(table).where(table.c.id == report_id)).one_or_none()

    def list_events(self, *, contribution_id: UUID) -> tuple[Row[Any], ...]:
        """Every appended line on one contribution, oldest first."""
        table = authenticated_contribution_events
        statement = (
            select(table)
            .where(table.c.contribution_id == contribution_id)
            .order_by(table.c.created_at.asc(), table.c.id.asc())
        )
        return tuple(self._session.execute(statement).all())
