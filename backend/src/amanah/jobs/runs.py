"""Collection runs: one bounded execution of one adapter against one source.

A run is the unit an operator dispatches and reads; the jobs underneath it are
the unit a worker claims. The two share the state machine in
`amanah.jobs.states` so `retry_wait` means the same thing in both places.

Bounds are validated here rather than at the route, because a run dispatched by
the scheduler deserves the same limits as one dispatched by an administrator.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.content import CollectionRun
from amanah.db.models.sources import Source
from amanah.domain.enums import CollectionMode, JobState
from amanah.jobs.service import LeaseLostError
from amanah.jobs.states import assert_transition

logger = logging.getLogger(__name__)

#: Widest window a single run may cover. A backfill spans years by slicing
#: itself into windows this size, never by asking for all of it at once.
MAXIMUM_WINDOW_DAYS = 400

#: Hard ceiling on the items one run may canonicalize, whoever dispatched it.
MAXIMUM_ITEM_CAP = 5_000

#: Default when a dispatch does not name one, so no run is ever unbounded.
DEFAULT_ITEM_CAP = 500


class RunValidationError(ValueError):
    """A dispatch asked for something outside the configured bounds.

    Carries a field name so the API can return a `422` naming what to fix,
    without echoing anything the caller did not already send.
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


class RunDispatch:
    """A validated request to run one adapter once."""

    def __init__(
        self,
        *,
        source_key: str,
        mode: CollectionMode,
        adapter_version: str,
        idempotency_key: str,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
        item_cap: int | None = None,
        source_seed_entry_id: UUID | None = None,
        requested_by: UUID | None = None,
    ) -> None:
        self.source_key = source_key
        self.mode = mode
        self.adapter_version = adapter_version
        self.idempotency_key = idempotency_key
        self.window_start = window_start
        self.window_end = window_end
        self.item_cap = DEFAULT_ITEM_CAP if item_cap is None else item_cap
        self.source_seed_entry_id = source_seed_entry_id
        self.requested_by = requested_by


def validate_dispatch(dispatch: RunDispatch) -> None:
    """Refuse an out-of-bounds dispatch before anything is written.

    Windows must be ordered, bounded, and not in the future; caps must be
    positive and under the ceiling. Failing here keeps a bad request from
    becoming a run row an operator then has to cancel.
    """
    start, end = dispatch.window_start, dispatch.window_end
    if (start is None) != (end is None):
        raise RunValidationError("window", "A window needs both a start and an end.")
    if start is not None and end is not None:
        if end < start:
            raise RunValidationError("window", "The window end precedes its start.")
        if end - start > timedelta(days=MAXIMUM_WINDOW_DAYS):
            raise RunValidationError(
                "window", f"A run may cover at most {MAXIMUM_WINDOW_DAYS} days."
            )
        if end > datetime.now(UTC) + timedelta(days=1):
            raise RunValidationError("window", "The window end is in the future.")
    if dispatch.item_cap < 1:
        raise RunValidationError("item_cap", "The item cap must be at least 1.")
    if dispatch.item_cap > MAXIMUM_ITEM_CAP:
        raise RunValidationError("item_cap", f"The item cap may not exceed {MAXIMUM_ITEM_CAP}.")


class CollectionRunService:
    """Owns every transition of `collection_runs`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def dispatch(self, dispatch: RunDispatch) -> tuple[CollectionRun, bool]:
        """Create the run, or return the one this dispatch already created.

        Returns `(run, is_new)`. Redelivering the same dispatch is a no-op rather
        than a second run, because `idempotency_key` describes what was asked
        for, not who asked.
        """
        validate_dispatch(dispatch)
        source = self._session.execute(
            select(Source).where(Source.source_key == dispatch.source_key)
        ).scalar_one_or_none()
        if source is None:
            raise RunValidationError("source_key", "No source is configured under that key.")
        # A fixture run is exempt: proving the pipeline end to end must not
        # require enabling a live connector.
        if not source.is_enabled and dispatch.mode is not CollectionMode.fixture:
            raise RunValidationError("source_key", "That source is not enabled for collection.")

        statement = (
            insert(CollectionRun)
            .values(
                source_id=source.id,
                source_seed_entry_id=dispatch.source_seed_entry_id,
                idempotency_key=dispatch.idempotency_key,
                mode=dispatch.mode,
                adapter_version=dispatch.adapter_version,
                window_start=dispatch.window_start,
                window_end=dispatch.window_end,
                item_cap=dispatch.item_cap,
                requested_by=dispatch.requested_by,
            )
            .on_conflict_do_nothing(index_elements=[CollectionRun.idempotency_key])
            .returning(CollectionRun.id)
        )
        created = self._session.execute(statement).scalar_one_or_none()
        if created is None:
            self._session.commit()
            existing = self._session.execute(
                select(CollectionRun).where(
                    CollectionRun.idempotency_key == dispatch.idempotency_key
                )
            ).scalar_one()
            logger.info("run dispatch absorbed a duplicate", extra={"run_id": str(existing.id)})
            return existing, False

        self._session.commit()
        run = self._session.get_one(CollectionRun, created)
        logger.info(
            "run dispatched",
            extra={"run_id": str(run.id), "mode": run.mode.value, "item_cap": run.item_cap},
        )
        return run, True

    def start(self, run: CollectionRun, *, owner: str, lease_seconds: int) -> None:
        """Take the run, refusing if another worker got there first."""
        assert_transition(run.status, JobState.running)
        now = datetime.now(UTC)
        claimed = self._session.execute(
            update(CollectionRun)
            .where(
                CollectionRun.id == run.id,
                CollectionRun.status.in_((JobState.queued, JobState.retry_wait)),
            )
            .values(
                status=JobState.running,
                lease_owner=owner,
                lease_expires_at=now + timedelta(seconds=lease_seconds),
                attempt=CollectionRun.attempt + 1,
            )
            .returning(CollectionRun.id)
        ).scalar_one_or_none()
        if claimed is None:
            self._session.rollback()
            raise LeaseLostError(run.id, owner)
        self._session.commit()
        self._session.refresh(run)

    def finish(
        self,
        run: CollectionRun,
        *,
        owner: str,
        status: JobState,
        counts: dict[str, Any] | None = None,
        coverage_warnings: list[str] | None = None,
        safe_error_code: str | None = None,
        cursor: str | None = None,
    ) -> None:
        """Settle the run and publish its counts and coverage.

        Counts and coverage are written with the terminal status in one
        statement, so a reader never sees a finished run whose numbers have not
        landed yet — the state on which "is this a gap or a zero?" depends.
        """
        assert_transition(run.status, status)
        now = datetime.now(UTC)
        values: dict[str, Any] = {
            "status": status,
            "lease_owner": None,
            "lease_expires_at": None,
            "safe_error_code": safe_error_code,
            "completed_at": now,
        }
        if counts is not None:
            values["counts"] = counts
        if coverage_warnings is not None:
            values["coverage_warnings"] = coverage_warnings
        if cursor is not None:
            values["cursor"] = cursor
        if status is JobState.failed and run.attempt >= run.max_attempts:
            values["is_dead_lettered"] = True

        settled = self._session.execute(
            update(CollectionRun)
            .where(
                CollectionRun.id == run.id,
                CollectionRun.status == JobState.running,
                CollectionRun.lease_owner == owner,
            )
            .values(**values)
            .returning(CollectionRun.id)
        ).scalar_one_or_none()
        if settled is None:
            self._session.rollback()
            raise LeaseLostError(run.id, owner)

        if status is JobState.succeeded:
            self._session.execute(
                update(Source)
                .where(Source.id == run.source_id)
                .values(last_success_at=now, last_checked_at=now)
            )
        else:
            self._session.execute(
                update(Source).where(Source.id == run.source_id).values(last_checked_at=now)
            )
        self._session.commit()
        self._session.refresh(run)
        logger.info(
            "run finished",
            extra={
                "run_id": str(run.id),
                "status": status.value,
                "safe_error_code": safe_error_code,
            },
        )

    def checkpoint_cursor(self, run: CollectionRun, cursor: str | None) -> None:
        """Persist the adapter's resume point without settling the run."""
        self._session.execute(
            update(CollectionRun).where(CollectionRun.id == run.id).values(cursor=cursor)
        )
        self._session.commit()
        self._session.refresh(run)

    def recover_expired_leases(self, *, now: datetime | None = None) -> int:
        """Return runs whose worker vanished to `queued`, or dead-letter them."""
        moment = now if now is not None else datetime.now(UTC)
        expired = (
            CollectionRun.status == JobState.running,
            CollectionRun.lease_expires_at < moment,
        )
        exhausted = list(
            self._session.execute(
                update(CollectionRun)
                .where(*expired, CollectionRun.attempt >= CollectionRun.max_attempts)
                .values(
                    status=JobState.failed,
                    lease_owner=None,
                    lease_expires_at=None,
                    safe_error_code="lease_expired",
                    is_dead_lettered=True,
                    completed_at=moment,
                )
                .returning(CollectionRun.id)
            ).scalars()
        )
        requeued = list(
            self._session.execute(
                update(CollectionRun)
                .where(*expired)
                .values(
                    status=JobState.queued,
                    lease_owner=None,
                    lease_expires_at=None,
                    next_run_at=moment,
                    safe_error_code="lease_expired",
                )
                .returning(CollectionRun.id)
            ).scalars()
        )
        self._session.commit()
        return len(exhausted) + len(requeued)
