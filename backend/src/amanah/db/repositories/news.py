"""Reads for the context news stream (B-S9.8).

Reads `authenticated_news`, which has no column for a hate label, a score, a
severity, or a review state — so the route serving it could not attach one even
by accident.

Ordering and windowing both use `COALESCE(published_at, retrieved_at)`. An
article whose feed gave no publication date still belongs in the window it was
collected for, and dropping it silently would make the window look emptier than
it was; substituting the retrieval time for *display* would be a different and
worse mistake, so the substitution happens only in the ordering expression and
`published_at` is still published as null.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Row, func, literal, select, tuple_
from sqlalchemy.orm import Session

from amanah.db.pagination import decode_keyset_cursor, encode_keyset_cursor
from amanah.db.views import authenticated_news, authenticated_source_status

#: Ordering name carried by every news cursor.
NEWS_ORDER_KEY = "news_published_at"


@dataclass(frozen=True, slots=True)
class NewsPage:
    """One page of the stream, plus the coverage a reader needs to interpret it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None
    total_in_window: int
    sources: tuple[str, ...]
    last_successful_run: datetime | None
    warnings: tuple[str, ...]


def _effective_time() -> ColumnElement[Any]:
    table = authenticated_news
    return func.coalesce(table.c.published_at, table.c.retrieved_at)


class NewsRepository:
    """The context news stream."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def read_window(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        limit: int,
        cursor: str | None = None,
    ) -> NewsPage:
        table = authenticated_news
        effective = _effective_time()
        in_window = (effective >= window_start, effective <= window_end)

        statement = select(table).where(*in_window)
        if cursor is not None:
            key_value, row_id = decode_keyset_cursor(cursor, NEWS_ORDER_KEY)
            statement = statement.where(
                # Bound parameters, not inlined values: a cursor is caller input.
                tuple_(effective, table.c.id) < tuple_(literal(key_value), literal(row_id))
            )
        statement = statement.order_by(effective.desc(), table.c.id.desc()).limit(limit + 1)
        rows = tuple(self._session.execute(statement).all())

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            boundary = last.published_at or last.retrieved_at
            next_cursor = encode_keyset_cursor(NEWS_ORDER_KEY, boundary, last.id)

        total = self._session.execute(
            select(func.count()).select_from(table).where(*in_window)
        ).scalar_one()
        sources = tuple(
            self._session.execute(
                select(table.c.source_name)
                .where(*in_window)
                .distinct()
                .order_by(table.c.source_name)
            ).scalars()
        )
        return NewsPage(
            rows=rows,
            next_cursor=next_cursor,
            total_in_window=int(total),
            sources=sources,
            last_successful_run=self._last_successful_run(),
            warnings=self._coverage_warnings(),
        )

    def _last_successful_run(self) -> datetime | None:
        """The newest successful collection across the configured news sources."""
        status = authenticated_source_status
        latest = self._session.execute(
            select(func.max(status.c.last_success_at)).where(status.c.kind == "news")
        ).scalar_one()
        return latest if isinstance(latest, datetime) else None

    def _coverage_warnings(self) -> tuple[str, ...]:
        """Publishable warnings attached to the news connectors."""
        status = authenticated_source_status
        warnings = self._session.execute(
            select(status.c.safe_warning)
            .where(status.c.kind == "news", status.c.safe_warning.isnot(None))
            .distinct()
        ).scalars()
        return tuple(str(warning) for warning in warnings)
