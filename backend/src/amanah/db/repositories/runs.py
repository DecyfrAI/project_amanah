"""Administrator reads of collection runs and their jobs.

Like every other repository here, these read an `authenticated_*` projection and
never a base table. The projections carry an administrator predicate of their
own, so a reviewer or base-role caller who reached this code would still get an
empty result rather than operational state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Row, literal, select, tuple_
from sqlalchemy.orm import Session

from amanah.api.schemas.runs import RUN_ORDER_KEY
from amanah.db.pagination import decode_keyset_cursor, encode_keyset_cursor
from amanah.db.views import authenticated_background_jobs, authenticated_collection_runs
from amanah.domain.enums import JobState


@dataclass(frozen=True, slots=True)
class RunPage:
    """One page of runs plus the cursor that continues it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None


class CollectionRunRepository:
    """Run and job state for `/v1/admin/runs`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_runs(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        source_key: str | None = None,
        status: JobState | None = None,
    ) -> RunPage:
        """Return one page of runs, newest dispatch first.

        The ordering pairs `started_at` with `id` so two runs dispatched in the
        same millisecond still have a defined page boundary.
        """
        table = authenticated_collection_runs
        statement = select(table)
        if source_key is not None:
            statement = statement.where(table.c.source_key == source_key)
        if status is not None:
            statement = statement.where(table.c.status == status.value)
        if cursor is not None:
            key_value, row_id = decode_keyset_cursor(cursor, RUN_ORDER_KEY)
            statement = statement.where(
                # Bound parameters, not inlined values: a cursor is caller input.
                tuple_(table.c.started_at, table.c.id) < tuple_(literal(key_value), literal(row_id))
            )

        statement = statement.order_by(table.c.started_at.desc(), table.c.id.desc()).limit(
            limit + 1
        )
        rows = tuple(self._session.execute(statement).all())

        if len(rows) <= limit:
            return RunPage(rows=rows, next_cursor=None)
        page = rows[:limit]
        last = page[-1]
        return RunPage(
            rows=page,
            next_cursor=encode_keyset_cursor(RUN_ORDER_KEY, last.started_at, last.id),
        )

    def get_run(self, run_id: UUID) -> Row[Any] | None:
        table = authenticated_collection_runs
        return self._session.execute(select(table).where(table.c.id == run_id)).one_or_none()

    def list_jobs(self, run_id: UUID) -> tuple[Row[Any], ...]:
        """Every stage of one run, in the order the pipeline produced them."""
        table = authenticated_background_jobs
        statement = (
            select(table)
            .where(table.c.collection_run_id == run_id)
            .order_by(table.c.created_at.asc(), table.c.id.asc())
        )
        return tuple(self._session.execute(statement).all())
