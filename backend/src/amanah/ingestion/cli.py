"""`amanah-etl` — the one command that runs collection.

`AGENTS.md` names this command, and `spec.md` section 10.6 requires the scheduled
pipeline and a manual dispatch to be *the same* command. They are: the scheduler
calls it with `--source`, an operator calls it with `--source` and a window, and
both produce a `collection_runs` row with its mode recorded, so a run's
provenance always says how it was started.

`--dry-run` performs discovery and canonicalization and writes no content. It
exists so an operator can see what a source would collect before letting it,
which matters most for the adapters that spend provider quota.

The worker connects with the service's own credentials and no verified caller, so
it is not scoped by the request-time identity the API publishes. That is correct
for a background process and it is also why nothing here reads an
`authenticated_*` projection: a worker writes base tables, and the API is the
only thing that reads through the views.
"""

from __future__ import annotations

import argparse
import logging
import socket
import sys
from datetime import UTC, date, datetime, time, timedelta
from os import getpid
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from amanah.canonical.encryption import build_cipher
from amanah.db.models.content import CollectionRun
from amanah.db.session import create_database_engine
from amanah.domain.enums import CollectionMode, JobState
from amanah.ingestion.backfill import DEFAULT_WINDOW_DAYS, BackfillPlanner, plan_backfill
from amanah.ingestion.configuration import (
    load_seed_configuration,
    load_source_configuration,
    project_seeds,
    project_sources,
)
from amanah.ingestion.contract import AdapterError, DiscoveryRequest, SourceAdapter
from amanah.ingestion.pipeline import CollectionPipeline, utc_now
from amanah.ingestion.registry import UnknownSourceError, build_default_registry
from amanah.jobs.runs import CollectionRunService, RunDispatch, RunValidationError
from amanah.ml.batch import DEFAULT_BATCH_SIZE, analyze
from amanah.ml.budgets import TokenBudget
from amanah.ml.catalog import build_registry
from amanah.ml.classification import ClassificationService
from amanah.ml.gemini import GeminiClient
from amanah.observability.logging import configure_logging
from amanah.settings import ConfigurationError, Settings, load_settings

logger = logging.getLogger("amanah.etl")

#: Cap on stages processed in one invocation. A run that needs more is resumed by
#: the next invocation from its checkpoint rather than looping without bound.
MAXIMUM_STAGES_PER_INVOCATION = 5_000

#: Window `analyze` covers when the caller names none. Wide enough to pick up a
#: backlog left by a failed run, narrow enough that a scheduled invocation does
#: not rescan the whole corpus every eight hours.
DEFAULT_ANALYSIS_WINDOW_DAYS = 7


def _worker_id() -> str:
    """An opaque identifier for this process's leases.

    The host name is included because an operator debugging a stuck lease needs
    to know which machine holds it. It never reaches an API response: the admin
    projection has no column for a lease owner.
    """
    return f"{socket.gethostname()}:{getpid()}:{uuid4().hex[:8]}"


def _parse_date(value: str) -> datetime:
    return datetime.combine(date.fromisoformat(value), time.min, tzinfo=UTC)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="amanah-etl", description="Run bounded collection.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="Dispatch and process one collection run.")
    run.add_argument("--source", required=True, help="Configured source key.")
    run.add_argument(
        "--mode", choices=["scheduled", "manual", "backfill", "fixture"], default="scheduled"
    )
    run.add_argument("--from", dest="window_start", type=_parse_date, default=None)
    run.add_argument("--to", dest="window_end", type=_parse_date, default=None)
    run.add_argument("--item-cap", type=int, default=None)
    run.add_argument(
        "--idempotency-key",
        default=None,
        help="Natural key of the work. Defaults to source, mode, and window.",
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and canonicalize without writing any content.",
    )

    backfill = subcommands.add_parser(
        "backfill", help="Dispatch resumable historical windows through the same pipeline."
    )
    backfill.add_argument("--source", required=True, help="Configured source key.")
    backfill.add_argument("--from", dest="window_start", type=_parse_date, default=None)
    backfill.add_argument("--to", dest="window_end", type=_parse_date, default=None)
    backfill.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    backfill.add_argument("--item-cap", type=int, default=None)
    backfill.add_argument(
        "--max-windows",
        type=int,
        default=12,
        help="Windows to dispatch in this invocation; the rest wait for the next.",
    )

    analyze = subcommands.add_parser(
        "analyze",
        help="Classify collected items and rebuild the deterministic metric buckets.",
    )
    analyze.add_argument("--from", dest="window_start", type=_parse_date, default=None)
    analyze.add_argument("--to", dest="window_end", type=_parse_date, default=None)
    analyze.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Items to classify in this invocation; the rest wait for the next.",
    )

    configure = subcommands.add_parser(
        "sync-config", help="Project the reviewed source and seed catalogue into the database."
    )
    configure.add_argument("--directory", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code rather than raising."""
    arguments = build_parser().parse_args(argv)
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    configure_logging(settings.log_level)

    if settings.database_url is None:
        logger.error("collection requires a configured database")
        return 2

    engine = create_database_engine(settings)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as session:
            if arguments.command == "sync-config":
                return _sync_config(session, arguments.directory)
            if arguments.command == "backfill":
                return _backfill(session, settings, arguments)
            if arguments.command == "analyze":
                return _analyze(session, settings, arguments)
            return _run(session, settings, arguments)
    finally:
        engine.dispose()


def _sync_config(session: Session, directory: str | None) -> int:
    from pathlib import Path

    path = Path(directory) if directory else None
    sources = load_source_configuration(path)
    seeds = load_seed_configuration(path)
    if sources.config_version != seeds.config_version:
        # The two files are one reviewed artifact. Versions that disagree mean
        # one of them was edited without the review that produced the other.
        logger.error(
            "source and seed configuration versions disagree",
            extra={"sources": sources.config_version, "seeds": seeds.config_version},
        )
        return 2
    written_sources = project_sources(session, sources)
    written_seeds = project_seeds(session, seeds)
    logger.info(
        "configuration synchronised",
        extra={"sources": written_sources, "approved_seeds": written_seeds},
    )
    return 0


def _analyze(session: Session, settings: Settings, arguments: argparse.Namespace) -> int:
    """Classify what has been collected, then recompute the buckets over it.

    Runs whether or not Gemini is configured. With no key every item defers and
    the aggregation still writes true observed counts and an honest coverage
    score, which is what keeps the dashboard useful without AI.

    The token budget is per invocation. That is the run boundary `spec.md`
    section 11.2 describes, and it means a scheduled analysis cannot spend more
    than its share however large the backlog is.
    """
    window_end = arguments.window_end or utc_now()
    window_start = arguments.window_start or window_end - timedelta(
        days=DEFAULT_ANALYSIS_WINDOW_DAYS
    )

    client = GeminiClient(
        settings=settings,
        registry=build_registry(),
        budget=TokenBudget(
            per_run_tokens=settings.gemini_per_run_token_budget,
            daily_tokens=settings.gemini_daily_token_budget,
        ),
    )
    if not client.is_configured:
        logger.warning(
            "classification is disabled",
            extra={"reason": "gemini_not_configured"},
        )

    result = analyze(
        session,
        classifier=ClassificationService(session, client=client),
        window_start=window_start,
        window_end=window_end,
        batch_size=arguments.batch_size,
    )
    session.commit()

    logger.info(
        "analysis complete",
        extra={
            "classified": result.classified,
            "deferred": result.deferred,
            "buckets_written": result.aggregation.buckets_written,
            "strata": [stratum.value for stratum in result.aggregation.strata],
        },
    )
    return 0


def _run(session: Session, settings: Settings, arguments: argparse.Namespace) -> int:
    sources = load_source_configuration(settings.source_config_directory)
    seeds = load_seed_configuration(settings.source_config_directory)
    registry = build_default_registry(sources)

    try:
        adapter = registry.build(arguments.source, settings=settings, sources=sources, seeds=seeds)
    except UnknownSourceError:
        logger.error("no adapter is registered for that source", extra={"source": arguments.source})
        return 2

    mode = CollectionMode(arguments.mode)
    dispatch = RunDispatch(
        source_key=arguments.source,
        mode=mode,
        adapter_version=adapter.adapter_version,
        idempotency_key=arguments.idempotency_key or _default_key(arguments, mode),
        window_start=arguments.window_start,
        window_end=arguments.window_end,
        item_cap=arguments.item_cap,
    )
    try:
        run, is_new = CollectionRunService(session).dispatch(dispatch)
    except RunValidationError as exc:
        logger.error("dispatch refused", extra={"field": exc.field})
        return 2

    if not is_new and run.status in {JobState.succeeded, JobState.policy_blocked}:
        logger.info("run already completed", extra={"run_id": str(run.id)})
        return 0

    if arguments.dry_run:
        return _dry_run(adapter, run)

    return _execute(session, settings, adapter, run)


def _dry_run(adapter: SourceAdapter, run: CollectionRun) -> int:
    """Discover and canonicalize without writing content.

    Nothing is persisted, including the run's own progress, so a dry run cannot
    be mistaken later for a real one.
    """
    try:
        result = adapter.discover(
            DiscoveryRequest(
                item_cap=run.item_cap or 0,
                window_start=run.window_start,
                window_end=run.window_end,
            )
        )
    except AdapterError as exc:
        logger.error("dry run stopped", extra={"safe_error_code": exc.safe_code})
        return 1

    logger.info(
        "dry run complete",
        extra={
            "discovered": len(result.references),
            "counts": dict(result.counts),
            "coverage_warnings": list(result.coverage_warnings),
        },
    )
    return 0


def _execute(
    session: Session, settings: Settings, adapter: SourceAdapter, run: CollectionRun
) -> int:
    key = settings.content_encryption_key
    pipeline = CollectionPipeline(
        session,
        adapter=adapter,
        worker_id=_worker_id(),
        cipher=build_cipher(key.get_secret_value() if key is not None else None),
    )
    pipeline.begin(run)

    processed = 0
    while processed < MAXIMUM_STAGES_PER_INVOCATION:
        outcome = pipeline.process_next()
        if outcome is None:
            break
        processed += 1

    pipeline.finish(run)
    session.refresh(run)
    logger.info(
        "run complete",
        extra={
            "run_id": str(run.id),
            "status": run.status.value,
            "stages": processed,
            "counts": run.counts,
        },
    )
    return 0 if run.status is JobState.succeeded else 1


def _default_key(arguments: argparse.Namespace, mode: CollectionMode) -> str:
    """A natural key describing the work, so a repeated dispatch is absorbed.

    Built from what the run *is* — source, mode, window — and never from the
    moment it was launched, because a key containing a timestamp would make every
    redelivery a new run and defeat the idempotency it is meant to provide.
    """
    start = arguments.window_start.date().isoformat() if arguments.window_start else "open"
    end = arguments.window_end.date().isoformat() if arguments.window_end else "open"
    return f"{arguments.source}:{mode.value}:{start}:{end}"


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())


def _backfill(session: Session, settings: Settings, arguments: argparse.Namespace) -> int:
    """Dispatch historical windows, then process whatever is queued.

    Windows are dispatched oldest first and processed in the same invocation, so
    a scheduled backfill makes steady progress without a second command. Each
    invocation is bounded by `--max-windows`; the rest wait, and the next call
    resumes from the first window that has not succeeded.
    """
    sources = load_source_configuration(settings.source_config_directory)
    seeds = load_seed_configuration(settings.source_config_directory)
    registry = build_default_registry(sources)
    try:
        adapter = registry.build(arguments.source, settings=settings, sources=sources, seeds=seeds)
    except UnknownSourceError:
        logger.error("no adapter is registered for that source", extra={"source": arguments.source})
        return 2

    plan = plan_backfill(
        source_key=arguments.source,
        start=arguments.window_start,
        end=arguments.window_end,
        window_days=arguments.window_days,
        item_cap=arguments.item_cap,
    )
    progress = BackfillPlanner(session).dispatch(
        plan, adapter_version=adapter.adapter_version, limit=arguments.max_windows
    )

    failures = 0
    for run in progress.dispatched:
        if _execute(session, settings, adapter, run) != 0:
            failures += 1

    logger.info(
        "backfill pass complete",
        extra={
            "windows_total": len(plan.windows),
            "dispatched": len(progress.dispatched),
            "already_complete": progress.already_complete,
            "remaining": progress.remaining,
            "failed": failures,
        },
    )
    return 1 if failures else 0
