"""Reviewer reads of the queue and its decision history (B-S17.4).

Both projections carry `amanah_is_reviewer()` in their own `WHERE` clause, so a
base-role caller who somehow reached this code gets an empty result rather than a
queue. Neither view has a column for the user who disputed a prediction: a
reviewer decides on the model's output, and knowing who complained could only
bias that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Row, literal, select, tuple_
from sqlalchemy.orm import Session

from amanah.db.pagination import decode_keyset_cursor, encode_keyset_cursor
from amanah.db.views import authenticated_review_events, authenticated_review_tasks
from amanah.domain.enums import ReviewTaskStatus, ReviewTaskType

#: Names the ordering a review-queue cursor belongs to.
REVIEW_QUEUE_ORDER_KEY = "review_priority_created_at"


@dataclass(frozen=True, slots=True)
class ReviewTaskPage:
    """One page of the queue plus the cursor that continues it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None


class ReviewRepository:
    """Reads the review queue and the decisions appended to it."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_tasks(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        status: ReviewTaskStatus | None = None,
        task_type: ReviewTaskType | None = None,
    ) -> ReviewTaskPage:
        """Return one page of the queue, highest priority and oldest first.

        Oldest-first within a priority band is deliberate: a queue ordered
        newest-first starves the disputes that have been waiting longest, which
        are exactly the ones somebody is still waiting on an answer for.

        The cursor pairs `created_at` with `id` rather than priority, because
        priority is not unique and a page boundary has to be a single row.
        """
        table = authenticated_review_tasks
        statement = select(table)
        if status is not None:
            statement = statement.where(table.c.status == status.value)
        if task_type is not None:
            statement = statement.where(table.c.task_type == task_type.value)
        if cursor is not None:
            key_value, row_id = decode_keyset_cursor(cursor, REVIEW_QUEUE_ORDER_KEY)
            statement = statement.where(
                tuple_(table.c.created_at, table.c.id) > tuple_(literal(key_value), literal(row_id))
            )
        statement = statement.order_by(
            table.c.priority.desc(), table.c.created_at.asc(), table.c.id.asc()
        ).limit(limit + 1)

        rows = tuple(self._session.execute(statement).all())
        if len(rows) <= limit:
            return ReviewTaskPage(rows=rows, next_cursor=None)
        page = rows[:limit]
        last = page[-1]
        return ReviewTaskPage(
            rows=page,
            next_cursor=encode_keyset_cursor(REVIEW_QUEUE_ORDER_KEY, last.created_at, last.id),
        )

    def get_task(self, task_id: UUID) -> Row[Any] | None:
        table = authenticated_review_tasks
        return self._session.execute(select(table).where(table.c.id == task_id)).one_or_none()

    def list_decisions(self, task_id: UUID) -> tuple[Row[Any], ...]:
        """Every decision appended to one task, oldest first.

        A later decision does not replace an earlier one. Two reviewers who
        disagreed both appear here, which is the record the append-only rule
        exists to keep.
        """
        table = authenticated_review_events
        statement = (
            select(table)
            .where(table.c.review_task_id == task_id)
            .order_by(table.c.created_at.asc(), table.c.id.asc())
        )
        return tuple(self._session.execute(statement).all())
