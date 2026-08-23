"""Orchestration: one run, three checkpointed stages, one item at a time.

The shape is deliberate. `discover` runs once per run and fans out to one `fetch`
job **per reference**, and that fan-out is what makes `rules/backend.md`'s "one
failed item must not fail unrelated work" true rather than aspirational: an
article that 404s dead-letters its own job while its twenty siblings proceed.

Each stage writes its output and enqueues its successor in one transaction
(`JobService.succeed`), so no stage ever starts against output that was not
stored. Re-running any stage converges: discovery is keyed on the reference,
`fetch` on the reference, `normalize` on the canonical item's natural key, and
every enqueue is idempotent on a key derived from the work rather than the
delivery.

Nothing here knows what a provider looks like. It moves `SourceReference` and
`CanonicalContentItem` values between stages and lets the adapter translate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from amanah.canonical.encryption import ContentCipher
from amanah.canonical.store import ContentStore
from amanah.db.models.content import CollectionRun
from amanah.db.models.jobs import BackgroundJob
from amanah.db.models.sources import Source, SourceSeedEntry
from amanah.domain.enums import JobStage, JobState
from amanah.ingestion.codec import (
    PayloadDecodeError,
    decode_item,
    decode_reference,
    encode_item,
    encode_reference,
)
from amanah.ingestion.contract import (
    AdapterError,
    CanonicalContentItem,
    DiscoveryRequest,
    SourceAdapter,
    SourceReference,
)
from amanah.jobs.runs import CollectionRunService
from amanah.jobs.service import JobService, LeaseLostError

logger = logging.getLogger(__name__)

#: Safe code recorded when a stage payload cannot be decoded. A stage that cannot
#: read its own input is broken, not unlucky, so this never retries.
MALFORMED_PAYLOAD_CODE = "stage_payload_malformed"

#: Safe code for an unexpected failure inside a stage. The exception itself goes
#: to the logs, because it can name internal hosts and carry source text.
INTERNAL_STAGE_CODE = "stage_failed"


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """What processing one job did, for the caller's counters."""

    stage: JobStage
    state: JobState
    counts: dict[str, int]


class CollectionPipeline:
    """Runs one adapter's work through the job queue."""

    def __init__(
        self,
        session: Session,
        *,
        adapter: SourceAdapter,
        worker_id: str,
        cipher: ContentCipher | None = None,
    ) -> None:
        self._session = session
        self._adapter = adapter
        self._worker_id = worker_id
        self._jobs = JobService(session)
        self._runs = CollectionRunService(session)
        self._store = ContentStore(session, cipher=cipher)

    # -- starting a run ---------------------------------------------------

    def begin(self, run: CollectionRun) -> BackgroundJob:
        """Claim the run and queue its discovery stage.

        The adapter version is stamped onto the run here rather than at dispatch:
        a dispatch records what was asked for, and only the worker knows which
        implementation actually answered.
        """
        self._runs.start(run, owner=self._worker_id, lease_seconds=_run_lease_seconds(run))
        run.adapter_version = self._adapter.adapter_version
        self._session.commit()
        return self._jobs.enqueue(
            collection_run_id=run.id,
            stage=JobStage.discover,
            idempotency_key=f"{run.id}:discover",
        )

    # -- processing one job ----------------------------------------------

    def process_next(self) -> StageOutcome | None:
        """Claim and process one job, or return `None` when the queue is empty."""
        job = self._jobs.claim_next(worker_id=self._worker_id)
        if job is None:
            return None
        return self.process(job)

    def process(self, job: BackgroundJob) -> StageOutcome:
        """Run one claimed job through its stage and settle it.

        Every failure is converted here, once, into a safe code and a retry
        decision. An `AdapterError` already carries that judgement; anything else
        is an internal fault and is neither retried nor described to the caller.
        """
        try:
            if job.stage is JobStage.discover:
                counts = self._discover(job)
            elif job.stage is JobStage.fetch:
                counts = self._fetch(job)
            else:
                counts = self._normalize(job)
        except PayloadDecodeError:
            logger.exception("stage payload could not be decoded", extra={"job_id": str(job.id)})
            self._jobs.fail(
                job, owner=self._worker_id, safe_error_code=MALFORMED_PAYLOAD_CODE, retryable=False
            )
            return StageOutcome(stage=job.stage, state=JobState.failed, counts={})
        except AdapterError as exc:
            if exc.is_policy_block:
                self._jobs.block(job, owner=self._worker_id, safe_error_code=exc.safe_code)
                return StageOutcome(stage=job.stage, state=JobState.policy_blocked, counts={})
            state = self._jobs.fail(
                job,
                owner=self._worker_id,
                safe_error_code=exc.safe_code,
                retryable=exc.is_retryable,
            )
            return StageOutcome(stage=job.stage, state=state, counts={})
        except LeaseLostError:
            # Someone else owns this job now. Dropping the work is correct:
            # retrying the write would overwrite whatever they did with it.
            logger.warning("job lease was lost mid-stage", extra={"job_id": str(job.id)})
            return StageOutcome(stage=job.stage, state=JobState.queued, counts={})
        except Exception:
            logger.exception("stage failed", extra={"job_id": str(job.id)})
            self._jobs.fail(
                job, owner=self._worker_id, safe_error_code=INTERNAL_STAGE_CODE, retryable=False
            )
            return StageOutcome(stage=job.stage, state=JobState.failed, counts={})

        return StageOutcome(stage=job.stage, state=JobState.succeeded, counts=counts)

    # -- the stages -------------------------------------------------------

    def _discover(self, job: BackgroundJob) -> dict[str, int]:
        run = self._session.get_one(CollectionRun, job.collection_run_id)
        result = self._adapter.discover(
            DiscoveryRequest(
                item_cap=run.item_cap or 0,
                cursor=run.cursor,
                window_start=run.window_start,
                window_end=run.window_end,
            )
        )
        checkpoint = self._adapter.checkpoint(result)
        self._runs.checkpoint_cursor(run, checkpoint.cursor)

        # One `fetch` job per reference. The first is enqueued inside the same
        # transaction that stores discovery's checkpoint; the rest follow, each
        # keyed on the reference so a re-run adds nothing.
        references = list(result.references)
        if not references:
            self._jobs.succeed(
                job,
                owner=self._worker_id,
                checkpoint={
                    "cursor": checkpoint.cursor,
                    "counts": dict(checkpoint.counts),
                    "coverage_warnings": list(checkpoint.coverage_warnings),
                },
            )
            return dict(checkpoint.counts)

        first, rest = references[0], references[1:]
        self._jobs.succeed(
            job,
            owner=self._worker_id,
            checkpoint={
                "cursor": checkpoint.cursor,
                "counts": dict(checkpoint.counts),
                "coverage_warnings": list(checkpoint.coverage_warnings),
                "reference_ids": [reference.reference_id for reference in references],
            },
            next_stage=JobStage.fetch,
            next_idempotency_key=_fetch_key(run.id, first),
            next_payload=encode_reference(first),
        )
        for reference in rest:
            self._jobs.enqueue(
                collection_run_id=run.id,
                stage=JobStage.fetch,
                idempotency_key=_fetch_key(run.id, reference),
                payload=encode_reference(reference),
            )
        return dict(checkpoint.counts)

    def _fetch(self, job: BackgroundJob) -> dict[str, int]:
        """Retrieve one reference and translate it into the canonical shape.

        Canonicalization happens here rather than in a stage of its own, so what
        crosses into `normalize` is already the canonical shape. An adapter that
        retrieves during discovery — news and YouTube both do, to avoid a second
        request or a second unit of quota — carries the item's provider metadata
        on its reference; that stays inside `background_jobs.payload`, which no
        projection has a column for.
        """
        reference = decode_reference(job.payload)
        payload = self._adapter.fetch(reference)
        item = self._adapter.canonicalize(payload)
        if item.is_fixture != self._adapter.is_fixture:
            # A fixture record presented as live — or the reverse — must never
            # reach storage, where the distinction becomes invisible.
            raise AdapterError("fixture_status_mismatch")

        encoded = encode_item(item)
        self._jobs.succeed(
            job,
            owner=self._worker_id,
            checkpoint={"source_item_id": item.source_item_id},
            next_stage=JobStage.normalize,
            next_idempotency_key=f"{job.collection_run_id}:normalize:{item.source_item_id}",
            next_payload=encoded,
        )
        return {"fetched": 1}

    def _normalize(self, job: BackgroundJob) -> dict[str, int]:
        item = decode_item(job.payload)
        source_id = self._source_id(item.source_key)
        stored = self._store.upsert(
            item,
            source_id=source_id,
            collection_run_id=job.collection_run_id,
            source_seed_entry_id=self._seed_entry_id(item),
        )
        self._jobs.succeed(
            job,
            owner=self._worker_id,
            checkpoint={
                "content_item_id": str(stored.content_item_id),
                "is_new": stored.is_new,
                "is_duplicate": stored.is_duplicate,
            },
        )
        if stored.is_duplicate:
            return {"deduplicated": 1}
        return {"stored": 1} if stored.is_new else {"updated": 1}

    # -- finishing a run --------------------------------------------------

    def finish(self, run: CollectionRun) -> None:
        """Settle the run from what its jobs actually did.

        Counts are derived from the job rows rather than from an in-memory
        tally, so a run that resumed in a second process still reports the whole
        of its own work.
        """
        counts, warnings, failures = self._summarize(run.id)
        status = JobState.succeeded if not failures else JobState.failed
        self._runs.finish(
            run,
            owner=self._worker_id,
            status=status,
            counts=counts,
            coverage_warnings=warnings,
            safe_error_code=failures[0] if failures else None,
        )

    def _summarize(self, run_id: UUID) -> tuple[dict[str, int], list[str], list[str]]:
        jobs = (
            self._session.execute(
                select(BackgroundJob).where(BackgroundJob.collection_run_id == run_id)
            )
            .scalars()
            .all()
        )
        counts: dict[str, int] = {}
        warnings: list[str] = []
        failures: list[str] = []
        for job in jobs:
            checkpoint: dict[str, Any] = job.checkpoint or {}
            for key, value in (checkpoint.get("counts") or {}).items():
                counts[str(key)] = counts.get(str(key), 0) + int(value)
            for warning in checkpoint.get("coverage_warnings") or []:
                if warning not in warnings:
                    warnings.append(str(warning))
            if job.stage is JobStage.normalize and job.state is JobState.succeeded:
                bucket = (
                    "deduplicated"
                    if checkpoint.get("is_duplicate")
                    else ("stored" if checkpoint.get("is_new") else "updated")
                )
                counts[bucket] = counts.get(bucket, 0) + 1
            if job.state is JobState.failed and job.safe_error_code:
                failures.append(job.safe_error_code)
        if failures:
            # A partly failed run is a coverage gap, stated plainly. It is never
            # published as a complete count, because a reader would then take an
            # undercount for a real decline.
            warnings.append(
                f"{len(failures)} item(s) in this run could not be collected, "
                "so its counts cover part of the window only."
            )
        return counts, warnings, failures

    # -- lookups ----------------------------------------------------------

    def _source_id(self, source_key: str) -> UUID:
        source_id = self._session.execute(
            select(Source.id).where(Source.source_key == source_key)
        ).scalar_one_or_none()
        if source_id is None:
            raise AdapterError("source_not_configured")
        return source_id

    def _seed_entry_id(self, item: CanonicalContentItem) -> UUID | None:
        """Resolve the approved seed row this item came from, if any.

        Looked up by `(registry_key, config_version)` — the documented identity —
        so an item collected under one configuration version can never be
        attributed to another.
        """
        if item.seed is None:
            return None
        return self._session.execute(
            select(SourceSeedEntry.id).where(
                SourceSeedEntry.registry_key == item.seed.registry_key,
                SourceSeedEntry.config_version == item.seed.config_version,
            )
        ).scalar_one_or_none()


def _fetch_key(run_id: UUID, reference: SourceReference) -> str:
    return f"{run_id}:fetch:{reference.reference_id}"


def _run_lease_seconds(run: CollectionRun) -> int:
    """How long a run's claim is held, scaled to how much it may collect."""
    del run
    return 900


def utc_now() -> datetime:
    return datetime.now(UTC)
