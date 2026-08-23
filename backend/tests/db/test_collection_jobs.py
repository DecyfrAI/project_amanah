"""Run and job state machines against a real database (B-S7.7).

These commit, because the properties under test are exactly the ones that only
exist once work is durable: a claim another worker can see, a checkpoint that
survives a crash, a lease that expires. The `clean_database` fixture truncates
between tests, so committing here does not leak into the next one.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from amanah.db.models.content import CollectionRun
from amanah.db.models.jobs import BackgroundJob
from amanah.domain.enums import CollectionMode, JobStage, JobState
from amanah.jobs.runs import (
    MAXIMUM_ITEM_CAP,
    CollectionRunService,
    RunDispatch,
    RunValidationError,
)
from amanah.jobs.service import JobService, LeaseLostError
from amanah.jobs.states import InvalidJobTransitionError
from tests.db import factories

WORKER = "worker-a"
OTHER_WORKER = "worker-b"


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as active:
        yield active


@pytest.fixture
def second_session(engine: Engine) -> Iterator[Session]:
    """A genuinely separate connection, so concurrency is real rather than mimed."""
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as active:
        yield active


@pytest.fixture
def source_key(engine: Engine) -> str:
    with engine.begin() as connection:
        factories.insert_source(connection, source_key="fixture_news")
    return "fixture_news"


@pytest.fixture
def run(engine: Engine, source_key: str) -> CollectionRun:
    del source_key
    with engine.begin() as connection:
        source_id = connection.execute(text("SELECT id FROM public.sources LIMIT 1")).scalar_one()
        run_id = factories.insert_collection_run(connection, source_id=source_id)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as active:
        return active.get_one(CollectionRun, run_id)


def _dispatch(**overrides: object) -> RunDispatch:
    values: dict[str, object] = {
        "source_key": "fixture_news",
        "mode": CollectionMode.fixture,
        "adapter_version": "fixture-1",
        "idempotency_key": f"dispatch-{uuid4()}",
    }
    values.update(overrides)
    return RunDispatch(**values)  # type: ignore[arg-type]


# -- runs -----------------------------------------------------------------


def test_redelivering_a_dispatch_does_not_start_a_second_run(
    session: Session, source_key: str
) -> None:
    """B-S7.2: the idempotency key describes the work, not the delivery."""
    del source_key
    service = CollectionRunService(session)
    dispatch = _dispatch()

    first, first_is_new = service.dispatch(dispatch)
    second, second_is_new = service.dispatch(dispatch)

    assert first_is_new
    assert not second_is_new
    assert first.id == second.id
    assert session.execute(select(CollectionRun)).scalars().all() == [first]


def test_a_dispatch_without_a_cap_is_still_bounded(session: Session, source_key: str) -> None:
    del source_key
    run, _ = CollectionRunService(session).dispatch(_dispatch())

    assert run.item_cap is not None
    assert 0 < run.item_cap <= MAXIMUM_ITEM_CAP


def test_an_oversized_cap_is_refused_before_anything_is_written(
    session: Session, source_key: str
) -> None:
    del source_key
    with pytest.raises(RunValidationError) as raised:
        CollectionRunService(session).dispatch(_dispatch(item_cap=MAXIMUM_ITEM_CAP + 1))

    assert raised.value.field == "item_cap"
    assert session.execute(select(CollectionRun)).scalars().all() == []


def test_a_half_specified_window_is_refused(session: Session, source_key: str) -> None:
    del source_key
    with pytest.raises(RunValidationError) as raised:
        CollectionRunService(session).dispatch(_dispatch(window_start=datetime.now(UTC)))

    assert raised.value.field == "window"


def test_an_unknown_source_key_is_refused(session: Session, source_key: str) -> None:
    del source_key
    with pytest.raises(RunValidationError) as raised:
        CollectionRunService(session).dispatch(_dispatch(source_key="not-configured"))

    assert raised.value.field == "source_key"


def test_only_one_worker_can_start_a_run(
    session: Session, second_session: Session, source_key: str
) -> None:
    del source_key
    run, _ = CollectionRunService(session).dispatch(_dispatch())
    # Both workers read the run while it is still queued: the race is decided by
    # the conditional update, not by whichever of them loaded it more recently.
    contender = second_session.get_one(CollectionRun, run.id)

    CollectionRunService(session).start(run, owner=WORKER, lease_seconds=60)

    with pytest.raises(LeaseLostError):
        CollectionRunService(second_session).start(contender, owner=OTHER_WORKER, lease_seconds=60)


def test_finishing_a_run_publishes_its_counts_and_coverage(
    session: Session, source_key: str
) -> None:
    """A finished run with no numbers would read as a zero rather than a gap."""
    del source_key
    run, _ = CollectionRunService(session).dispatch(_dispatch())
    service = CollectionRunService(session)
    service.start(run, owner=WORKER, lease_seconds=60)
    service.finish(
        run,
        owner=WORKER,
        status=JobState.succeeded,
        counts={"discovered": 3, "stored": 2},
        coverage_warnings=["One feed was unreachable for this window."],
    )

    assert run.status is JobState.succeeded
    assert run.counts == {"discovered": 3, "stored": 2}
    assert run.coverage_warnings == ["One feed was unreachable for this window."]
    assert run.completed_at is not None
    assert run.lease_owner is None


# -- jobs -----------------------------------------------------------------


def test_enqueueing_the_same_stage_twice_yields_one_job(
    session: Session, run: CollectionRun
) -> None:
    """B-S7.7, duplicate delivery."""
    service = JobService(session)
    key = f"{run.id}:discover"

    first = service.enqueue(collection_run_id=run.id, stage=JobStage.discover, idempotency_key=key)
    second = service.enqueue(collection_run_id=run.id, stage=JobStage.discover, idempotency_key=key)

    assert first.id == second.id
    assert len(session.execute(select(BackgroundJob)).scalars().all()) == 1


def test_two_workers_never_claim_the_same_job(
    session: Session, second_session: Session, run: CollectionRun
) -> None:
    """B-S7.3, concurrency. Two real connections compete for one row."""
    JobService(session).enqueue(
        collection_run_id=run.id, stage=JobStage.discover, idempotency_key=f"{run.id}:discover"
    )

    claimed = JobService(session).claim_next(worker_id=WORKER)
    contender = JobService(second_session).claim_next(worker_id=OTHER_WORKER)

    assert claimed is not None
    assert contender is None


def test_a_claim_consumes_an_attempt_and_records_its_holder(
    session: Session, run: CollectionRun
) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.discover, idempotency_key=f"{run.id}:discover"
    )

    job = service.claim_next(worker_id=WORKER, lease_seconds=60)

    assert job is not None
    assert job.state is JobState.running
    assert job.attempt == 1
    assert job.lease_owner == WORKER
    assert job.lease_expires_at is not None


def test_a_job_that_is_not_yet_available_is_not_claimed(
    session: Session, run: CollectionRun
) -> None:
    later = datetime.now(UTC) + timedelta(hours=1)
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id,
        stage=JobStage.discover,
        idempotency_key=f"{run.id}:discover",
        available_at=later,
    )

    assert service.claim_next(worker_id=WORKER) is None


def test_success_checkpoints_this_stage_before_the_next_one_exists(
    session: Session, run: CollectionRun
) -> None:
    """B-S7.4. Both writes commit together, so the follow-on stage can never
    start against output that was not stored."""
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.discover, idempotency_key=f"{run.id}:discover"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    queued = service.succeed(
        job,
        owner=WORKER,
        checkpoint={"references": 4},
        next_stage=JobStage.fetch,
        next_idempotency_key=f"{run.id}:fetch",
        next_payload={"references": 4},
    )

    assert job.state is JobState.succeeded
    assert job.checkpoint == {"references": 4}
    assert job.completed_at is not None
    assert queued is not None
    assert queued.stage is JobStage.fetch
    assert queued.payload == {"references": 4}


def test_a_follow_on_stage_requires_its_own_idempotency_key(
    session: Session, run: CollectionRun
) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.discover, idempotency_key=f"{run.id}:discover"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    with pytest.raises(ValueError, match="idempotency key"):
        service.succeed(job, owner=WORKER, next_stage=JobStage.fetch)


def test_a_retryable_failure_waits_instead_of_dying(session: Session, run: CollectionRun) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    outcome = service.fail(job, owner=WORKER, safe_error_code="provider_timeout", retryable=True)

    assert outcome is JobState.retry_wait
    assert job.state is JobState.retry_wait
    assert job.available_at > datetime.now(UTC)
    assert job.safe_error_code == "provider_timeout"
    assert not job.is_dead_lettered


def test_a_permanent_failure_dead_letters_immediately(session: Session, run: CollectionRun) -> None:
    """A rejected URL or an unapproved licence never becomes retryable."""
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    outcome = service.fail(job, owner=WORKER, safe_error_code="unsupported_source", retryable=False)

    assert outcome is JobState.failed
    assert job.is_dead_lettered
    assert job.completed_at is not None


def test_the_retry_budget_is_finite(session: Session, run: CollectionRun) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id,
        stage=JobStage.fetch,
        idempotency_key=f"{run.id}:fetch",
        max_attempts=2,
    )

    outcome = JobState.queued
    claimed: BackgroundJob | None = None
    for _ in range(2):
        claimed = service.claim_next(worker_id=WORKER, now=datetime.now(UTC) + timedelta(hours=1))
        assert claimed is not None
        outcome = service.fail(
            claimed, owner=WORKER, safe_error_code="provider_timeout", retryable=True
        )

    assert outcome is JobState.failed
    assert claimed is not None
    assert claimed.is_dead_lettered


def test_a_policy_block_is_neither_retried_nor_dead_lettered(
    session: Session, run: CollectionRun
) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    service.block(job, owner=WORKER, safe_error_code="source_terms_prohibit_collection")

    assert job.state is JobState.policy_blocked
    assert not job.is_dead_lettered


def test_a_worker_that_lost_its_lease_cannot_settle_the_job(
    session: Session, run: CollectionRun
) -> None:
    """B-S7.7, lease loss. The stale holder's write must match no row."""
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    with pytest.raises(LeaseLostError):
        service.succeed(job, owner=OTHER_WORKER, checkpoint={"stolen": True})

    session.refresh(job)
    assert job.state is JobState.running


def test_an_expired_lease_returns_the_job_to_the_queue(
    session: Session, run: CollectionRun
) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER, lease_seconds=1)
    assert job is not None

    recovered = service.recover_expired_leases(now=datetime.now(UTC) + timedelta(minutes=5))

    session.refresh(job)
    assert recovered == 1
    assert job.state is JobState.queued
    assert job.lease_owner is None
    # The crashed attempt was still spent, so the budget is not silently refilled.
    assert job.attempt == 1


def test_an_expired_lease_with_no_budget_left_becomes_a_dead_letter(
    session: Session, run: CollectionRun
) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id,
        stage=JobStage.fetch,
        idempotency_key=f"{run.id}:fetch",
        max_attempts=1,
    )
    job = service.claim_next(worker_id=WORKER, lease_seconds=1)
    assert job is not None

    service.recover_expired_leases(now=datetime.now(UTC) + timedelta(minutes=5))

    session.refresh(job)
    assert job.state is JobState.failed
    assert job.is_dead_lettered


def test_one_failing_stage_does_not_disturb_an_unrelated_one(
    session: Session, run: CollectionRun
) -> None:
    """B-S7.7, partial failure. `rules/backend.md`: one failed item must not fail
    unrelated work."""
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch:a"
    )
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch:b"
    )

    first = service.claim_next(worker_id=WORKER)
    assert first is not None
    service.fail(first, owner=WORKER, safe_error_code="provider_timeout", retryable=False)
    second = service.claim_next(worker_id=OTHER_WORKER)

    assert second is not None
    assert second.id != first.id
    assert second.state is JobState.running


def test_a_settled_job_cannot_be_settled_again(session: Session, run: CollectionRun) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None
    service.succeed(job, owner=WORKER)

    with pytest.raises(InvalidJobTransitionError):
        service.succeed(job, owner=WORKER)


def test_a_running_job_is_not_cancelled_under_its_worker(
    session: Session, run: CollectionRun
) -> None:
    service = JobService(session)
    service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )
    job = service.claim_next(worker_id=WORKER)
    assert job is not None

    assert not service.cancel(job.id)

    session.refresh(job)
    assert job.state is JobState.running


def test_a_queued_job_can_be_cancelled(session: Session, run: CollectionRun) -> None:
    service = JobService(session)
    job = service.enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )

    assert service.cancel(job.id)

    session.refresh(job)
    assert job.state is JobState.cancelled
    assert service.claim_next(worker_id=WORKER) is None


def test_the_database_refuses_a_running_job_with_no_lease(
    session: Session, run: CollectionRun
) -> None:
    """The invariant is a constraint, not a convention: a direct write that
    breaks it is rejected too."""
    job = JobService(session).enqueue(
        collection_run_id=run.id, stage=JobStage.fetch, idempotency_key=f"{run.id}:fetch"
    )

    with pytest.raises(Exception, match="running_requires_lease"):
        session.execute(
            text("UPDATE public.background_jobs SET state = 'running' WHERE id = :id"),
            {"id": job.id},
        )
        session.commit()
    session.rollback()
