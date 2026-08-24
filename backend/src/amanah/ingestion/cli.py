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
from pathlib import Path
from uuid import uuid4

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from amanah.canonical.encryption import build_cipher
from amanah.db.models.content import CollectionRun
from amanah.db.session import create_database_engine
from amanah.domain.enums import CollectionMode, JobState
from amanah.ingestion.backfill import DEFAULT_WINDOW_DAYS, BackfillPlanner, plan_backfill
from amanah.ingestion.configuration import (
    config_directory,
    load_seed_configuration,
    load_source_configuration,
    project_seeds,
    project_sources,
)
from amanah.ingestion.contract import AdapterError, DiscoveryRequest, SourceAdapter
from amanah.ingestion.datapacks.importer import DatapackImporter
from amanah.ingestion.datapacks.manifest import DatapackManifest, verify_file
from amanah.ingestion.operations import (
    EtlValidationError,
    RedactedRunSummary,
    dispatch_from_environment,
    load_datapack_configuration,
    resolve_approved_datapack,
    validate_dispatch,
    write_redacted_summary,
)
from amanah.ingestion.pipeline import CollectionPipeline, utc_now
from amanah.ingestion.registry import (
    AdapterContext,
    SourceDisabledError,
    UnknownSourceError,
    build_default_registry,
)
from amanah.jobs.runs import CollectionRunService, RunDispatch, RunValidationError
from amanah.ml.batch import DEFAULT_BATCH_SIZE, analyze
from amanah.ml.budgets import TokenBudget
from amanah.ml.catalog import build_registry
from amanah.ml.classification import ClassificationService
from amanah.ml.gemini import GeminiClient
from amanah.observability.logging import configure_logging
from amanah.observability.metrics import MetricName, record_metric
from amanah.reporting.policies import load_policy_catalogue, project_policies
from amanah.settings import ConfigurationError, Settings, load_settings

logger = logging.getLogger("amanah.etl")

#: Cap on stages processed in one invocation. A run that needs more is resumed by
#: the next invocation from its checkpoint rather than looping without bound.
MAXIMUM_STAGES_PER_INVOCATION = 5_000

#: Window `analyze` covers when the caller names none.
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

    analyze_command = subcommands.add_parser(
        "analyze",
        help="Classify collected items and rebuild the deterministic metric buckets.",
    )
    analyze_command.add_argument("--from", dest="window_start", type=_parse_date, default=None)
    analyze_command.add_argument("--to", dest="window_end", type=_parse_date, default=None)
    analyze_command.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Items to classify in this invocation; the rest wait for the next.",
    )

    configure = subcommands.add_parser(
        "sync-config",
        help="Project the reviewed source, seed, and platform-policy catalogue.",
    )
    configure.add_argument("--directory", default=None)

    subcommands.add_parser(
        "validate-config", help="Validate schedule inputs against reviewed configuration."
    )
    orchestrate = subcommands.add_parser(
        "run-from-env",
        help="Run every configured ETL stage from the constrained environment contract.",
    )
    orchestrate.add_argument(
        "--summary-path", default="work/etl-run-summary.json", help=argparse.SUPPRESS
    )
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
            if arguments.command in {"validate-config", "run-from-env"}:
                return _scheduled(
                    session,
                    settings,
                    arguments,
                    validate_only=arguments.command == "validate-config",
                )
            if arguments.command == "sync-config":
                return _sync_config(session, arguments.directory)
            if arguments.command == "backfill":
                return _backfill(session, settings, arguments)
            if arguments.command == "analyze":
                return _analyze(session, settings, arguments)
            return _run(session, settings, arguments)
    finally:
        engine.dispose()


def _scheduled(
    session: Session,
    settings: Settings,
    arguments: argparse.Namespace,
    *,
    validate_only: bool,
) -> int:
    """Validate and execute the exact contract shared by cron and manual dispatch."""
    try:
        sources = load_source_configuration(settings.source_config_directory)
        seeds = load_seed_configuration(settings.source_config_directory)
        configuration_directory = config_directory(settings.source_config_directory)
        datapacks = load_datapack_configuration(configuration_directory)
        dispatch = validate_dispatch(
            dispatch_from_environment(), sources=sources, seeds=seeds, datapacks=datapacks
        )
    except (EtlValidationError, OSError, ValueError, yaml.YAMLError):
        logger.error("scheduled dispatch refused", extra={"safe_error_code": "etl_config_invalid"})
        return 2
    if validate_only:
        logger.info(
            "scheduled configuration valid",
            extra={"sources": list(dispatch.sources), "item_cap": dispatch.item_cap},
        )
        return 0

    if (
        _sync_config(
            session,
            str(settings.source_config_directory) if settings.source_config_directory else None,
        )
        != 0
    ):
        return 2
    started = utc_now()
    window_start, window_end = _incremental_window(started)
    summaries: list[RedactedRunSummary] = []
    failures = 0
    for source_key in dispatch.sources:
        idempotency_key = (
            f"{source_key}:fixture:{window_end.isoformat()}"
            if source_key == "fixtures"
            else f"{source_key}:scheduled:{window_start.isoformat()}:{window_end.isoformat()}"
        )
        namespace = argparse.Namespace(
            source=source_key,
            mode="fixture" if source_key == "fixtures" else "scheduled",
            window_start=None if source_key == "fixtures" else window_start,
            window_end=None if source_key == "fixtures" else window_end,
            item_cap=dispatch.item_cap,
            idempotency_key=idempotency_key,
            dry_run=dispatch.dry_run,
        )
        code = _run(session, settings, namespace, selected_registry_keys=dispatch.registry_keys)
        failures += int(code != 0)
        row = session.execute(
            select(CollectionRun).where(CollectionRun.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        summaries.append(
            RedactedRunSummary(
                source=source_key,
                status=(
                    "validated"
                    if dispatch.dry_run
                    else (row.status.value if row is not None else "failed")
                ),
                started_at=started.isoformat(),
                completed_at=utc_now().isoformat(),
                counts=dict(row.counts or {}) if row is not None else {},
                coverage_warnings=tuple(row.coverage_warnings or ()) if row is not None else (),
                safe_error_codes=(
                    (row.safe_error_code,)
                    if row is not None and row.safe_error_code
                    else (() if code == 0 else ("etl_source_failed",))
                ),
                run_id=str(row.id) if row is not None else None,
            )
        )
        record_metric(
            MetricName.connector_runs,
            source_key=source_key,
            outcome="succeeded" if code == 0 else "failed",
        )
        if code != 0:
            record_metric(
                MetricName.connector_failures,
                source_key=source_key,
                outcome="failed",
            )
    for manifest_id in dispatch.datapack_ids:
        package = datapacks.by_id(manifest_id)
        if package is None:  # already validated; keeps the type checker honest
            continue
        try:
            manifest_path, data_path = resolve_approved_datapack(
                package, repository_root=configuration_directory.parent
            )
            document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest = DatapackManifest.model_validate(document)
            if dispatch.dry_run:
                manifest.require_approved()
                verify_file(manifest, data_path)
                counts: dict[str, int] = {}
            else:
                imported = DatapackImporter(
                    session,
                    cipher=build_cipher(
                        settings.content_encryption_key.get_secret_value()
                        if settings.content_encryption_key is not None
                        else None
                    ),
                ).import_package(manifest, data_path)
                counts = {
                    "imported": imported.imported,
                    "skipped": imported.skipped,
                    "errors": imported.errors,
                }
        except Exception:
            session.rollback()
            failures += 1
            logger.error(
                "datapack import failed",
                extra={"safe_error_code": "datapack_import_failed"},
            )
            summaries.append(
                RedactedRunSummary(
                    source="open_datapack",
                    status="failed",
                    started_at=started.isoformat(),
                    completed_at=utc_now().isoformat(),
                    counts={},
                    safe_error_codes=("datapack_import_failed",),
                    run_id=manifest_id,
                )
            )
            continue
        summaries.append(
            RedactedRunSummary(
                source="open_datapack",
                status="validated" if dispatch.dry_run else "succeeded",
                started_at=started.isoformat(),
                completed_at=utc_now().isoformat(),
                counts=counts,
                safe_error_codes=(),
                run_id=manifest_id,
            )
        )
    if not dispatch.dry_run:
        analysis = argparse.Namespace(
            window_start=None, window_end=None, batch_size=DEFAULT_BATCH_SIZE
        )
        failures += int(_analyze(session, settings, analysis) != 0)
    write_redacted_summary(Path(arguments.summary_path), tuple(summaries))
    return 1 if failures else 0


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
    policies = load_policy_catalogue(path)
    written_sources = project_sources(session, sources)
    written_seeds = project_seeds(session, seeds)
    # The platform-policy catalogue is versioned on its own: a rule is
    # re-reviewed on the platform's schedule, not on the collection catalogue's,
    # so its `config_version` is deliberately not compared with the other two.
    written_policies = project_policies(session, policies)
    logger.info(
        "configuration synchronised",
        extra={
            "sources": written_sources,
            "approved_seeds": written_seeds,
            "platform_policies": written_policies,
        },
    )
    return 0


def _analyze(session: Session, settings: Settings, arguments: argparse.Namespace) -> int:
    """Classify what has been collected, then recompute its metric buckets."""
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
        logger.warning("classification is disabled", extra={"reason": "gemini_not_configured"})

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


def _run(
    session: Session,
    settings: Settings,
    arguments: argparse.Namespace,
    *,
    selected_registry_keys: tuple[str, ...] = (),
) -> int:
    sources = load_source_configuration(settings.source_config_directory)
    seeds = load_seed_configuration(settings.source_config_directory)
    if selected_registry_keys:
        seeds = seeds.model_copy(
            update={
                "seeds": tuple(
                    seed for seed in seeds.seeds if seed.registry_key in selected_registry_keys
                )
            }
        )
    registry = build_default_registry(sources)

    try:
        adapter = registry.build(
            arguments.source,
            AdapterContext(session=session, settings=settings, sources=sources, seeds=seeds),
        )
    except UnknownSourceError:
        logger.error("no adapter is registered for that source", extra={"source": arguments.source})
        return 2
    except SourceDisabledError:
        logger.warning("source is disabled", extra={"source": arguments.source})
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
    start = arguments.window_start.isoformat() if arguments.window_start else "open"
    end = arguments.window_end.isoformat() if arguments.window_end else "open"
    return f"{arguments.source}:{mode.value}:{start}:{end}"


def _incremental_window(moment: datetime) -> tuple[datetime, datetime]:
    """The previous closed eight-hour UTC bucket, stable across workflow retries."""
    boundary = moment.astimezone(UTC).replace(
        hour=(moment.astimezone(UTC).hour // 8) * 8,
        minute=0,
        second=0,
        microsecond=0,
    )
    return boundary - timedelta(hours=8), boundary


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
        adapter = registry.build(
            arguments.source,
            AdapterContext(session=session, settings=settings, sources=sources, seeds=seeds),
        )
    except (UnknownSourceError, SourceDisabledError):
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
