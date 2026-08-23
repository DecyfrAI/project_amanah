"""The job queue: enqueue, claim, checkpoint, and settle.

Every method here commits. A state transition that is only durable once some
caller remembers to commit is not a state machine, and a lease that is not
visible to other workers is not a lease.

Three invariants are enforced against the database rather than against the
in-memory object, because the in-memory object can be stale:

* **Enqueue is idempotent.** The unique `idempotency_key` is the natural key of
  the work. A duplicate dispatch finds the existing row.
* **A claim is conditional.** `FOR UPDATE SKIP LOCKED` hands one job to exactly
  one worker even when a dozen ask at the same moment.
* **A settlement proves ownership.** Every transition out of `running` matches on
  the lease owner as well as the id, so a worker whose lease expired and was
  reclaimed cannot overwrite the work of whoever picked the job up next.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.jobs import BackgroundJob
from amanah.domain.enums import JobStage, JobState
from amanah.jobs.backoff import next_attempt_at
from amanah.jobs.states import CLAIMABLE_STATES, assert_transition

logger = logging.getLogger(__name__)

#: Default retry budget for one stage. Deliberately small: a stage that has
#: failed five times is not going to succeed on the sixth, and a dead letter an
#: operator can see beats an invisible loop.
DEFAULT_MAX_ATTEMPTS = 5

#: How long a claim is good for before a recovery sweep may take it back. Long
#: enough for a bounded provider call, short enough that a crashed worker does
#: not park the job for an hour.
DEFAULT_LEASE_SECONDS = 300

#: Safe code recorded when a worker disappears mid-stage.
LEASE_EXPIRED_ERROR_CODE = "lease_expired"


class LeaseLostError(RuntimeError):
    """The job is no longer held by this worker.

    Raised when a settlement matches no row: the lease expired and the job was
    recovered, or another worker already settled it. The correct response is to
    drop the work, not to retry the write.
    """

    def __init__(self, job_id: UUID, owner: str) -> None:
        super().__init__(f"job {job_id} is not held by {owner}")
        self.job_id = job_id
        self.owner = owner


class JobService:
    """Owns every transition of `background_jobs`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- creating work ----------------------------------------------------

    def enqueue(
        self,
        *,
        collection_run_id: UUID,
        stage: JobStage,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        available_at: datetime | None = None,
    ) -> BackgroundJob:
        """Queue one stage, or return the job that already represents it.

        The insert is `ON CONFLICT DO NOTHING`, so a redelivered dispatch is
        absorbed by the database rather than by a read-then-write race that two
        workers could both lose.
        """
        job = self._enqueue_without_commit(
            collection_run_id=collection_run_id,
            stage=stage,
            idempotency_key=idempotency_key,
            payload=payload,
            max_attempts=max_attempts,
            available_at=available_at,
        )
        self._session.commit()
        return job

    def _enqueue_without_commit(
        self,
        *,
        collection_run_id: UUID,
        stage: JobStage,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        available_at: datetime | None = None,
    ) -> BackgroundJob:
        values: dict[str, Any] = {
            "collection_run_id": collection_run_id,
            "stage": stage,
            "idempotency_key": idempotency_key,
            "payload": payload or {},
            "max_attempts": max_attempts,
        }
        if available_at is not None:
            values["available_at"] = available_at

        statement = (
            insert(BackgroundJob)
            .values(**values)
            .on_conflict_do_nothing(index_elements=[BackgroundJob.idempotency_key])
            .returning(BackgroundJob.id)
        )
        inserted = self._session.execute(statement).scalar_one_or_none()
        if inserted is None:
            existing = self._session.execute(
                select(BackgroundJob).where(BackgroundJob.idempotency_key == idempotency_key)
            ).scalar_one()
            logger.info(
                "job enqueue absorbed a duplicate",
                extra={"job_id": str(existing.id), "stage": stage.value},
            )
            return existing
        return self._session.get_one(BackgroundJob, inserted)

    # -- taking work ------------------------------------------------------

    def claim_next(
        self,
        *,
        worker_id: str,
        stages: tuple[JobStage, ...] | None = None,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        now: datetime | None = None,
    ) -> BackgroundJob | None:
        """Claim the oldest eligible job, or return `None` when there is none.

        The inner `SELECT ... FOR UPDATE SKIP LOCKED` is what makes concurrent
        workers safe: a row another worker is already claiming is skipped rather
        than waited on, so no two workers can leave with the same job and none
        of them blocks.
        """
        moment = now if now is not None else datetime.now(UTC)
        candidate = (
            select(BackgroundJob.id)
            .where(
                BackgroundJob.state.in_(tuple(CLAIMABLE_STATES)),
                BackgroundJob.available_at <= moment,
            )
            .order_by(BackgroundJob.available_at, BackgroundJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if stages is not None:
            candidate = candidate.where(BackgroundJob.stage.in_(stages))

        claimed = self._session.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == candidate.scalar_subquery())
            .values(
                state=JobState.running,
                lease_owner=worker_id,
                lease_expires_at=moment + timedelta(seconds=lease_seconds),
                attempt=BackgroundJob.attempt + 1,
            )
            .returning(BackgroundJob.id)
        ).scalar_one_or_none()
        self._session.commit()

        if claimed is None:
            return None
        job = self._session.get_one(BackgroundJob, claimed)
        logger.info(
            "job claimed",
            extra={"job_id": str(job.id), "stage": job.stage.value, "attempt": job.attempt},
        )
        return job

    def recover_expired_leases(self, *, now: datetime | None = None) -> int:
        """Return abandoned jobs to the queue and dead-letter the exhausted ones.

        A crashed worker consumed an attempt, so recovery respects the retry
        budget: a job with attempts left goes back to `queued`, and one without
        becomes a visible dead letter rather than an invisible loop.
        """
        moment = now if now is not None else datetime.now(UTC)
        expired = (
            BackgroundJob.state == JobState.running,
            BackgroundJob.lease_expires_at < moment,
        )

        exhausted = self._session.execute(
            update(BackgroundJob)
            .where(*expired, BackgroundJob.attempt >= BackgroundJob.max_attempts)
            .values(
                state=JobState.failed,
                lease_owner=None,
                lease_expires_at=None,
                safe_error_code=LEASE_EXPIRED_ERROR_CODE,
                is_dead_lettered=True,
                completed_at=moment,
            )
            .returning(BackgroundJob.id)
        ).scalars()
        dead_lettered = list(exhausted)

        requeued = self._session.execute(
            update(BackgroundJob)
            .where(*expired)
            .values(
                state=JobState.queued,
                lease_owner=None,
                lease_expires_at=None,
                available_at=moment,
                safe_error_code=LEASE_EXPIRED_ERROR_CODE,
            )
            .returning(BackgroundJob.id)
        ).scalars()
        recovered = list(requeued)
        self._session.commit()

        if dead_lettered or recovered:
            logger.warning(
                "recovered expired job leases",
                extra={"requeued": len(recovered), "dead_lettered": len(dead_lettered)},
            )
        return len(recovered) + len(dead_lettered)

    # -- settling work ----------------------------------------------------

    def succeed(
        self,
        job: BackgroundJob,
        *,
        owner: str,
        checkpoint: dict[str, Any] | None = None,
        next_stage: JobStage | None = None,
        next_idempotency_key: str | None = None,
        next_payload: dict[str, Any] | None = None,
    ) -> BackgroundJob | None:
        """Record this stage's output and, in the same transaction, queue the next.

        The order inside the transaction is the point: the checkpoint is written
        first and the follow-on stage is inserted second, and both commit
        together. A crash between them is impossible, so the next stage can
        never start against output that was never stored.
        """
        assert_transition(job.state, JobState.succeeded)
        if next_stage is not None and next_idempotency_key is None:
            raise ValueError("a follow-on stage needs its own idempotency key")

        self._settle(
            job,
            owner=owner,
            state=JobState.succeeded,
            checkpoint=checkpoint,
            safe_error_code=None,
            completed_at=datetime.now(UTC),
        )
        queued: BackgroundJob | None = None
        if next_stage is not None and next_idempotency_key is not None:
            queued = self._enqueue_without_commit(
                collection_run_id=job.collection_run_id,
                stage=next_stage,
                idempotency_key=next_idempotency_key,
                payload=next_payload,
            )
        self._session.commit()
        logger.info(
            "job succeeded",
            extra={
                "job_id": str(job.id),
                "stage": job.stage.value,
                "next_stage": next_stage.value if next_stage else None,
            },
        )
        return queued

    def fail(
        self,
        job: BackgroundJob,
        *,
        owner: str,
        safe_error_code: str,
        retryable: bool,
        now: datetime | None = None,
    ) -> JobState:
        """Settle a failed attempt as a retry, or as a dead letter.

        A permanent failure never waits: `rules/backend.md` reserves backoff for
        transient problems, and retrying a rejected URL or an unapproved licence
        only spends the budget before an operator sees the code.
        """
        moment = now if now is not None else datetime.now(UTC)
        has_budget = retryable and job.attempt < job.max_attempts
        target = JobState.retry_wait if has_budget else JobState.failed
        assert_transition(job.state, target)

        if has_budget:
            self._settle(
                job,
                owner=owner,
                state=target,
                safe_error_code=safe_error_code,
                available_at=next_attempt_at(job.attempt, now=moment),
            )
        else:
            self._settle(
                job,
                owner=owner,
                state=target,
                safe_error_code=safe_error_code,
                is_dead_lettered=True,
                completed_at=moment,
            )
        self._session.commit()
        logger.warning(
            "job attempt failed",
            extra={
                "job_id": str(job.id),
                "stage": job.stage.value,
                "attempt": job.attempt,
                "safe_error_code": safe_error_code,
                "outcome": target.value,
            },
        )
        return target

    def block(self, job: BackgroundJob, *, owner: str, safe_error_code: str) -> None:
        """Stop the job for a policy reason. Never retried, never dead-lettered.

        A policy block is a correct outcome, not a fault: the source's terms, an
        approval gate, or a data-class rule said no. It stays distinguishable
        from `failed` so an operator does not go looking for a bug.
        """
        assert_transition(job.state, JobState.policy_blocked)
        self._settle(
            job,
            owner=owner,
            state=JobState.policy_blocked,
            safe_error_code=safe_error_code,
            completed_at=datetime.now(UTC),
        )
        self._session.commit()
        logger.info(
            "job policy blocked",
            extra={"job_id": str(job.id), "safe_error_code": safe_error_code},
        )

    def cancel(self, job_id: UUID) -> bool:
        """Cancel a job that has not started or is waiting to retry.

        A running job is left alone: cancelling under a live worker would race
        its settlement. It becomes cancellable again as soon as it settles or its
        lease expires.
        """
        cancelled = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job_id,
                BackgroundJob.state.in_((JobState.queued, JobState.retry_wait)),
            )
            .values(
                state=JobState.cancelled,
                lease_owner=None,
                lease_expires_at=None,
                completed_at=datetime.now(UTC),
            )
            .returning(BackgroundJob.id)
        ).scalar_one_or_none()
        self._session.commit()
        return cancelled is not None

    def _settle(
        self,
        job: BackgroundJob,
        *,
        owner: str,
        state: JobState,
        checkpoint: dict[str, Any] | None = None,
        safe_error_code: str | None = None,
        available_at: datetime | None = None,
        completed_at: datetime | None = None,
        is_dead_lettered: bool = False,
    ) -> None:
        """Apply one transition, but only if this worker still holds the lease."""
        values: dict[str, Any] = {
            "state": state,
            "lease_owner": None,
            "lease_expires_at": None,
            "safe_error_code": safe_error_code,
            "is_dead_lettered": is_dead_lettered,
        }
        if checkpoint is not None:
            values["checkpoint"] = checkpoint
        if available_at is not None:
            values["available_at"] = available_at
        if completed_at is not None:
            values["completed_at"] = completed_at

        settled = self._session.execute(
            update(BackgroundJob)
            .where(
                BackgroundJob.id == job.id,
                BackgroundJob.state == JobState.running,
                BackgroundJob.lease_owner == owner,
            )
            .values(**values)
            .returning(BackgroundJob.id)
        ).scalar_one_or_none()
        if settled is None:
            self._session.rollback()
            raise LeaseLostError(job.id, owner)
        self._session.refresh(job)
