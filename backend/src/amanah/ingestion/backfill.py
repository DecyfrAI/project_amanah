"""Bounded historical backfill (B-S24).

Five years of history is not a bigger run; it is many ordinary runs. This module
slices a long range into windows and dispatches each one through the *existing*
pipeline, with the same adapters, the same caps, the same registry and stratum
rules, and the same canonical storage. There is no new retrieval path here and
nothing that reaches a source outside approved configuration — which is the whole
point of `frontend-backend-reconciliation.md` section 2.8: the product owner
asked for history, not for a second way in.

Two properties do the real work.

**Resumability.** Each window's idempotency key is derived from the source and
the window's dates, so re-running a backfill skips the windows that already
succeeded and picks up where it stopped. An interruption costs one window, not
the whole span.

**Honest coverage.** Each window is its own run with its own counts and coverage,
and its mode is `backfill` rather than `scheduled`. A sparse window therefore
renders as a gap or as low coverage rather than as a real zero — which matters
most exactly here, because the further back a window sits the less of it any
source still serves, and a thin 2021 bucket shown as a genuine count would read
as a decline that never happened.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from amanah.db.models.content import CollectionRun
from amanah.domain.enums import CollectionMode, JobState
from amanah.jobs.runs import CollectionRunService, RunDispatch

logger = logging.getLogger(__name__)

#: Default slice width. Narrow enough that one window stays inside a run's item
#: cap for a busy source, wide enough that five years is a manageable number of
#: runs rather than eighteen hundred.
DEFAULT_WINDOW_DAYS = 30

#: Widest slice a backfill may use, matching the per-run window ceiling.
MAXIMUM_WINDOW_DAYS = 90

#: Roughly the five years the product owner asked for.
DEFAULT_BACKFILL_DAYS = 5 * 365


@dataclass(frozen=True, slots=True)
class BackfillWindow:
    """One slice of the historical range."""

    start: datetime
    end: datetime

    @property
    def key_fragment(self) -> str:
        return f"{self.start.date().isoformat()}:{self.end.date().isoformat()}"


@dataclass(frozen=True, slots=True)
class BackfillPlan:
    """Every window a backfill will cover, oldest first."""

    source_key: str
    windows: tuple[BackfillWindow, ...]
    item_cap: int | None


def slice_windows(
    *, start: datetime, end: datetime, window_days: int = DEFAULT_WINDOW_DAYS
) -> Iterator[BackfillWindow]:
    """Divide a range into contiguous, non-overlapping windows.

    Windows abut rather than overlap: each starts one second after the previous
    ended. An overlap would collect the boundary twice, and while dedupe would
    absorb the duplicates, it would also spend quota twice for nothing.
    """
    if end < start:
        raise ValueError("the backfill range ends before it starts")
    width = max(1, min(window_days, MAXIMUM_WINDOW_DAYS))

    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=width) - timedelta(seconds=1), end)
        yield BackfillWindow(start=cursor, end=window_end)
        cursor = window_end + timedelta(seconds=1)


def plan_backfill(
    *,
    source_key: str,
    start: datetime | None = None,
    end: datetime | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    item_cap: int | None = None,
) -> BackfillPlan:
    """Build the window list for one source, oldest first."""
    finish = end or datetime.now(UTC)
    begin = start or finish - timedelta(days=DEFAULT_BACKFILL_DAYS)
    return BackfillPlan(
        source_key=source_key,
        windows=tuple(slice_windows(start=begin, end=finish, window_days=window_days)),
        item_cap=item_cap,
    )


def backfill_idempotency_key(source_key: str, window: BackfillWindow) -> str:
    """The natural key of one backfilled window.

    Derived from the source and the window alone. Nothing about *when* the
    backfill was launched appears in it, which is what makes a resumed backfill
    recognise the windows it already finished instead of collecting them again.
    """
    return f"{source_key}:backfill:{window.key_fragment}"


@dataclass(frozen=True, slots=True)
class BackfillProgress:
    """What one pass over the plan dispatched, skipped, and left to do."""

    dispatched: tuple[CollectionRun, ...]
    already_complete: int
    remaining: int


class BackfillPlanner:
    """Dispatches a plan's windows as ordinary runs, skipping finished ones."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._runs = CollectionRunService(session)

    def dispatch(
        self, plan: BackfillPlan, *, adapter_version: str, limit: int | None = None
    ) -> BackfillProgress:
        """Create runs for the windows that are not already done.

        Returns after `limit` dispatches so one invocation stays bounded; the
        next call continues from the first window that still needs work.
        """
        dispatched: list[CollectionRun] = []
        complete = 0
        remaining = 0

        for window in plan.windows:
            key = backfill_idempotency_key(plan.source_key, window)
            if self._is_complete(key):
                complete += 1
                continue
            if limit is not None and len(dispatched) >= limit:
                remaining += 1
                continue

            run, _is_new = self._runs.dispatch(
                RunDispatch(
                    source_key=plan.source_key,
                    # `backfill`, never `scheduled`. A historical window and a
                    # live one produce different coverage, and a reader must be
                    # able to tell which they are looking at.
                    mode=CollectionMode.backfill,
                    adapter_version=adapter_version,
                    idempotency_key=key,
                    window_start=window.start,
                    window_end=window.end,
                    item_cap=plan.item_cap,
                )
            )
            dispatched.append(run)

        logger.info(
            "backfill dispatched",
            extra={
                "source_key": plan.source_key,
                "windows": len(plan.windows),
                "dispatched": len(dispatched),
                "already_complete": complete,
                "remaining": remaining,
            },
        )
        return BackfillProgress(
            dispatched=tuple(dispatched), already_complete=complete, remaining=remaining
        )

    def _is_complete(self, idempotency_key: str) -> bool:
        """Whether this window already ran to a terminal, non-retryable state.

        A failed window is *not* complete: it is dispatched again so a transient
        provider outage during a long backfill does not leave a permanent hole in
        the history.
        """
        status = self._session.execute(
            select(CollectionRun.status).where(CollectionRun.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        return status in {JobState.succeeded, JobState.policy_blocked, JobState.cancelled}
