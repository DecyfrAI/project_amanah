"""Reads of snapshot insights, threads, captures, and reaction counts (B-S27).

Reaction counts come from `authenticated_post_reactions`, which aggregates per
post and exposes only the *caller's* own reaction alongside. There is no query
here that could produce a per-author total, which is how ADR 0004's "reactions
never rank authors" survives contact with a reporting-minded future reader.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Row, literal, select, tuple_
from sqlalchemy.orm import Session

from amanah.db.pagination import decode_keyset_cursor, encode_keyset_cursor
from amanah.db.views import (
    authenticated_dashboard_captures,
    authenticated_discussion_posts,
    authenticated_post_reactions,
    authenticated_snapshot_insights,
)

#: Names the ordering an insight-list cursor belongs to.
INSIGHT_ORDER_KEY = "insight_created_at"

#: Names the ordering the caller's own note list uses.
VIEWER_POST_ORDER_KEY = "viewer_post_created_at"


@dataclass(frozen=True, slots=True)
class InsightPage:
    """One page of snapshot insights plus the cursor that continues it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class PostPage:
    """One page of notes plus the cursor that continues it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None


class DiscussionRepository:
    """Reads everything the insight and discussion endpoints publish."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- insights ---------------------------------------------------------

    def list_insights(self, *, limit: int, cursor: str | None = None) -> InsightPage:
        table = authenticated_snapshot_insights
        statement = select(table)
        if cursor is not None:
            key_value, row_id = decode_keyset_cursor(cursor, INSIGHT_ORDER_KEY)
            statement = statement.where(
                tuple_(table.c.created_at, table.c.id) < tuple_(literal(key_value), literal(row_id))
            )
        statement = statement.order_by(table.c.created_at.desc(), table.c.id.desc()).limit(
            limit + 1
        )
        rows = tuple(self._session.execute(statement).all())
        if len(rows) <= limit:
            return InsightPage(rows=rows, next_cursor=None)
        page = rows[:limit]
        last = page[-1]
        return InsightPage(
            rows=page,
            next_cursor=encode_keyset_cursor(INSIGHT_ORDER_KEY, last.created_at, last.id),
        )

    def get_insight(self, insight_id: UUID) -> Row[Any] | None:
        table = authenticated_snapshot_insights
        return self._session.execute(select(table).where(table.c.id == insight_id)).one_or_none()

    # -- threads ----------------------------------------------------------

    def list_thread(self, insight_id: UUID) -> tuple[Row[Any], ...]:
        """Every note on one insight, oldest first, retracted ones included.

        A retracted note keeps its place. Filtering it out here would make the
        thread read as though the turn never happened, which is precisely what
        ADR 0004's "nothing is silently deleted" rules out.
        """
        table = authenticated_discussion_posts
        statement = (
            select(table)
            .where(table.c.snapshot_insight_id == insight_id)
            .order_by(table.c.created_at.asc(), table.c.id.asc())
        )
        return tuple(self._session.execute(statement).all())

    def get_post(self, post_id: UUID) -> Row[Any] | None:
        """One note, read through the same projection a thread is read through."""
        table = authenticated_discussion_posts
        return self._session.execute(select(table).where(table.c.id == post_id)).one_or_none()

    def list_posts_by_author(
        self, author_id: UUID, *, limit: int, cursor: str | None = None
    ) -> PostPage:
        """One page of the notes written by one person, newest first."""
        table = authenticated_discussion_posts
        statement = select(table).where(table.c.user_id == author_id)
        if cursor is not None:
            key_value, row_id = decode_keyset_cursor(cursor, VIEWER_POST_ORDER_KEY)
            statement = statement.where(
                tuple_(table.c.created_at, table.c.id) < tuple_(literal(key_value), literal(row_id))
            )
        statement = statement.order_by(table.c.created_at.desc(), table.c.id.desc()).limit(
            limit + 1
        )
        rows = tuple(self._session.execute(statement).all())
        if len(rows) <= limit:
            return PostPage(rows=rows, next_cursor=None)
        page = rows[:limit]
        last = page[-1]
        return PostPage(
            rows=page,
            next_cursor=encode_keyset_cursor(VIEWER_POST_ORDER_KEY, last.created_at, last.id),
        )

    # -- reactions and captures -------------------------------------------

    def reaction_counts(self, post_ids: tuple[UUID, ...]) -> dict[UUID, Row[Any]]:
        """Per-post counts, keyed by post. One query for a whole thread."""
        if not post_ids:
            return {}
        table = authenticated_post_reactions
        rows = self._session.execute(
            select(table).where(table.c.discussion_post_id.in_(post_ids))
        ).all()
        return {row.discussion_post_id: row for row in rows}

    def captures(self, capture_ids: tuple[UUID, ...]) -> dict[UUID, Row[Any]]:
        """The captures attached to a set of notes, keyed by capture."""
        if not capture_ids:
            return {}
        table = authenticated_dashboard_captures
        rows = self._session.execute(select(table).where(table.c.id.in_(capture_ids))).all()
        return {row.id: row for row in rows}

    def get_capture(self, capture_id: UUID) -> Row[Any] | None:
        table = authenticated_dashboard_captures
        return self._session.execute(select(table).where(table.c.id == capture_id)).one_or_none()
