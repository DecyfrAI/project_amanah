"""Bounded historical backfill (B-S24.6).

Five years of history is many ordinary runs, so what is tested is the *planning*:
that windows tile the range without gaps or overlaps, that a resumed backfill
skips what already succeeded, that each window is provenanced as `backfill`
rather than as a scheduled run, and that a failed window is retried rather than
left as a permanent hole.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from amanah.db.models.content import CollectionRun, ContentItem
from amanah.domain.enums import CollectionMode, JobState
from amanah.ingestion.backfill import (
    MAXIMUM_WINDOW_DAYS,
    BackfillPlan,
    BackfillPlanner,
    backfill_idempotency_key,
    plan_backfill,
    slice_windows,
)
from amanah.ingestion.fixtures.adapter import FIXTURE_SOURCE_KEY, FixtureAdapter
from amanah.ingestion.pipeline import CollectionPipeline
from tests.db import factories

ADAPTER_VERSION = "fixtures-1.0.0"


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as active:
        yield active


@pytest.fixture
def fixture_source(engine: Engine) -> None:
    with engine.begin() as connection:
        factories.insert_source(connection, source_key=FIXTURE_SOURCE_KEY, name="Fixtures")


# -- window slicing -------------------------------------------------------


def test_windows_tile_the_range_without_gaps_or_overlaps() -> None:
    """An overlap collects a boundary twice and spends quota for nothing; a gap
    leaves a hole in the history nobody would notice."""
    start = datetime(2021, 1, 1, tzinfo=UTC)
    end = datetime(2021, 6, 30, tzinfo=UTC)

    windows = list(slice_windows(start=start, end=end, window_days=30))

    assert windows[0].start == start
    assert windows[-1].end == end
    for earlier, later in pairwise(windows):
        assert later.start == earlier.end + timedelta(seconds=1)


def test_a_window_never_exceeds_the_ceiling() -> None:
    windows = list(
        slice_windows(
            start=datetime(2021, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 1, tzinfo=UTC),
            window_days=10_000,
        )
    )

    for window in windows:
        assert window.end - window.start <= timedelta(days=MAXIMUM_WINDOW_DAYS)


def test_a_reversed_range_is_refused() -> None:
    with pytest.raises(ValueError, match="ends before it starts"):
        list(
            slice_windows(
                start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2021, 1, 1, tzinfo=UTC)
            )
        )


def test_five_years_becomes_a_manageable_number_of_runs() -> None:
    plan = plan_backfill(
        source_key=FIXTURE_SOURCE_KEY,
        start=datetime(2021, 8, 23, tzinfo=UTC),
        end=datetime(2026, 8, 23, tzinfo=UTC),
    )

    assert 55 <= len(plan.windows) <= 70


def test_the_window_key_does_not_depend_on_when_the_backfill_ran() -> None:
    """A key containing a timestamp would make every redelivery a new run and
    defeat the resumability it exists to provide."""
    window = next(
        slice_windows(start=datetime(2021, 1, 1, tzinfo=UTC), end=datetime(2021, 1, 31, tzinfo=UTC))
    )

    first = backfill_idempotency_key(FIXTURE_SOURCE_KEY, window)
    second = backfill_idempotency_key(FIXTURE_SOURCE_KEY, window)

    assert first == second
    assert "2021-01-01" in first


# -- dispatching ----------------------------------------------------------


def _plan(windows: int = 3) -> BackfillPlan:
    # Anchored so the range both covers the fixture corpus and ends in the
    # past: a dispatch whose window ends in the future is refused, which is the
    # correct behaviour and not something to work around here.
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return plan_backfill(
        source_key=FIXTURE_SOURCE_KEY,
        start=start,
        # A whole number of windows, so the last one ends where the tiling
        # does rather than a day short of it.
        end=start + timedelta(days=30 * windows) - timedelta(seconds=1),
        window_days=30,
        item_cap=50,
    )


def test_each_window_becomes_its_own_run(session: Session, fixture_source: None) -> None:
    del fixture_source
    plan = _plan()

    progress = BackfillPlanner(session).dispatch(plan, adapter_version=ADAPTER_VERSION)

    assert len(progress.dispatched) == len(plan.windows)
    stored = session.execute(select(func.count()).select_from(CollectionRun)).scalar_one()
    assert stored == len(plan.windows)


def test_every_backfilled_run_is_provenanced_as_a_backfill(
    session: Session, fixture_source: None
) -> None:
    """B-S24.4. A historical window and a live one produce different coverage,
    and a reader must be able to tell which they are looking at."""
    del fixture_source

    progress = BackfillPlanner(session).dispatch(_plan(), adapter_version=ADAPTER_VERSION)

    assert all(run.mode is CollectionMode.backfill for run in progress.dispatched)
    assert all(run.window_start is not None for run in progress.dispatched)
    assert all(run.item_cap == 50 for run in progress.dispatched)


def test_a_second_pass_dispatches_nothing_new(session: Session, fixture_source: None) -> None:
    """The keys are derived from the windows, so a re-run is absorbed."""
    del fixture_source
    plan = _plan()
    planner = BackfillPlanner(session)

    planner.dispatch(plan, adapter_version=ADAPTER_VERSION)
    planner.dispatch(plan, adapter_version=ADAPTER_VERSION)

    stored = session.execute(select(func.count()).select_from(CollectionRun)).scalar_one()
    assert stored == len(plan.windows)


def test_a_pass_is_bounded_and_the_rest_wait(session: Session, fixture_source: None) -> None:
    """One invocation stays bounded; the next continues from where it stopped."""
    del fixture_source
    plan = _plan(windows=5)

    progress = BackfillPlanner(session).dispatch(plan, adapter_version=ADAPTER_VERSION, limit=2)

    assert len(progress.dispatched) == 2
    assert progress.remaining == 3


def test_resuming_skips_the_windows_that_already_succeeded(
    session: Session, fixture_source: None
) -> None:
    """B-S24.6. An interruption costs one window, not the whole span."""
    del fixture_source
    plan = _plan()
    planner = BackfillPlanner(session)
    first = planner.dispatch(plan, adapter_version=ADAPTER_VERSION, limit=1)
    _complete(session, first.dispatched[0])

    second = planner.dispatch(plan, adapter_version=ADAPTER_VERSION)

    assert second.already_complete == 1
    assert len(second.dispatched) == len(plan.windows) - 1


def test_a_failed_window_is_dispatched_again(session: Session, fixture_source: None) -> None:
    """A transient outage during a long backfill must not leave a permanent hole
    in the history."""
    del fixture_source
    plan = _plan()
    planner = BackfillPlanner(session)
    first = planner.dispatch(plan, adapter_version=ADAPTER_VERSION, limit=1)
    run = first.dispatched[0]
    _fail(session, run)

    second = planner.dispatch(plan, adapter_version=ADAPTER_VERSION)

    assert second.already_complete == 0
    assert any(dispatched.id == run.id for dispatched in second.dispatched)


def test_a_backfilled_window_dedupes_against_content_already_ingested(
    session: Session, fixture_source: None
) -> None:
    """B-S24.4. The backfill goes through the same canonical pipeline, so a
    later run overlapping the same content converges rather than duplicating."""
    del fixture_source
    from amanah.jobs.runs import CollectionRunService, RunDispatch

    plan = _plan()
    for run in BackfillPlanner(session).dispatch(plan, adapter_version=ADAPTER_VERSION).dispatched:
        _run_pipeline(session, run)
    after_backfill = session.execute(select(func.count()).select_from(ContentItem)).scalar_one()
    assert after_backfill > 0

    overlapping, _ = CollectionRunService(session).dispatch(
        RunDispatch(
            source_key=FIXTURE_SOURCE_KEY,
            mode=CollectionMode.manual,
            adapter_version=ADAPTER_VERSION,
            idempotency_key="overlapping-manual-run",
            item_cap=50,
        )
    )
    _run_pipeline(session, overlapping)

    after_overlap = session.execute(select(func.count()).select_from(ContentItem)).scalar_one()
    assert after_overlap == after_backfill


def _run_pipeline(session: Session, run: CollectionRun) -> None:
    pipeline = CollectionPipeline(session, adapter=FixtureAdapter(), worker_id="backfill-worker")
    pipeline.begin(run)
    while pipeline.process_next() is not None:
        pass
    pipeline.finish(run)


def _complete(session: Session, run: CollectionRun) -> None:
    session.execute(
        update(CollectionRun)
        .where(CollectionRun.id == run.id)
        .values(status=JobState.succeeded, completed_at=datetime.now(UTC))
    )
    session.commit()


def _fail(session: Session, run: CollectionRun) -> None:
    session.execute(
        update(CollectionRun)
        .where(CollectionRun.id == run.id)
        .values(status=JobState.failed, completed_at=datetime.now(UTC))
    )
    session.commit()
