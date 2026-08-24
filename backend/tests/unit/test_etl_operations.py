"""Schedule dispatch stays within reviewed source/seed/datapack configuration."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from amanah.ingestion.cli import _incremental_window
from amanah.ingestion.configuration import (
    SeedConfiguration,
    SourceConfiguration,
    load_seed_configuration,
    load_source_configuration,
)
from amanah.ingestion.operations import (
    ApprovedDatapack,
    DatapackConfiguration,
    EtlDispatch,
    EtlValidationError,
    RedactedRunSummary,
    dispatch_from_environment,
    resolve_approved_datapack,
    validate_dispatch,
    write_redacted_summary,
)


def configured() -> tuple[SourceConfiguration, SeedConfiguration]:
    return load_source_configuration(), load_seed_configuration()


def test_fixture_schedule_is_valid_and_explicit() -> None:
    sources, seeds = configured()
    dispatch = EtlDispatch(sources=("fixtures",), item_cap=25)

    assert validate_dispatch(dispatch, sources=sources, seeds=seeds) is dispatch


def test_reviewed_configuration_versions_cannot_drift() -> None:
    sources, seeds = configured()
    mismatched_seeds = seeds.model_copy(update={"config_version": "different"})

    with pytest.raises(EtlValidationError, match="versions do not match"):
        validate_dispatch(
            EtlDispatch(sources=("fixtures",), item_cap=25),
            sources=sources,
            seeds=mismatched_seeds,
        )


@pytest.mark.parametrize("source_key", ["missing", "youtube"])
def test_unknown_or_disabled_source_is_refused(source_key: str) -> None:
    sources, seeds = configured()

    with pytest.raises(EtlValidationError):
        validate_dispatch(
            EtlDispatch(sources=(source_key,), item_cap=25), sources=sources, seeds=seeds
        )


def test_item_cap_cannot_exceed_schedule_ceiling() -> None:
    sources, seeds = configured()

    with pytest.raises(EtlValidationError):
        validate_dispatch(
            EtlDispatch(sources=("fixtures",), item_cap=1001), sources=sources, seeds=seeds
        )


def test_registry_key_requires_reviewed_version_and_matching_source() -> None:
    sources, seeds = configured()
    approved = next(seed for seed in seeds.seeds if seed.is_runnable)

    with pytest.raises(EtlValidationError):
        validate_dispatch(
            EtlDispatch(
                sources=("fixtures",),
                item_cap=25,
                registry_keys=(approved.registry_key,),
                config_version=seeds.config_version,
            ),
            sources=sources,
            seeds=seeds,
        )


def test_environment_contract_has_no_url_or_query_input() -> None:
    dispatch = dispatch_from_environment(
        {
            "ETL_SOURCES": "fixtures,fixtures",
            "ETL_MAX_ITEMS": "20",
            "ETL_DRY_RUN": "true",
            "ETL_REGISTRY_KEYS": "",
        }
    )

    assert dispatch.sources == ("fixtures",)
    assert dispatch.item_cap == 20
    assert dispatch.dry_run is True


def test_datapack_ids_are_allowlisted() -> None:
    sources, seeds = configured()
    datapacks = DatapackConfiguration(
        config_version=sources.config_version,
        packages=(
            ApprovedDatapack(
                manifest_id="approved",
                manifest_path=Path("datapacks/manifests/approved.yml"),
                data_path=Path("work/approved.csv"),
                is_enabled=True,
            ),
        ),
    )

    dispatch = EtlDispatch(sources=("fixtures",), item_cap=20, datapack_ids=("approved",))
    assert (
        validate_dispatch(dispatch, sources=sources, seeds=seeds, datapacks=datapacks) is dispatch
    )
    with pytest.raises(EtlValidationError):
        validate_dispatch(
            EtlDispatch(sources=("fixtures",), item_cap=20, datapack_ids=("other",)),
            sources=sources,
            seeds=seeds,
            datapacks=datapacks,
        )


def test_datapack_paths_cannot_escape_repository(tmp_path: Path) -> None:
    package = ApprovedDatapack(
        manifest_id="bad",
        manifest_path=Path("../outside.yml"),
        data_path=Path("work/file.csv"),
        is_enabled=True,
    )

    with pytest.raises(EtlValidationError):
        resolve_approved_datapack(package, repository_root=tmp_path)


def test_run_artifact_contains_only_safe_summary_fields(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    write_redacted_summary(
        path,
        (
            RedactedRunSummary(
                source="fixtures",
                status="succeeded",
                started_at="2026-08-23T00:00:00+00:00",
                completed_at="2026-08-23T00:01:00+00:00",
                counts={"stored": 2},
            ),
        ),
    )

    content = path.read_text(encoding="utf-8")
    assert "stored" in content
    assert "prompt" not in content
    assert "source_payload" not in content
    assert "canonical_url" not in content


def test_incremental_window_is_a_retry_stable_eight_hour_bucket() -> None:
    first = _incremental_window(datetime(2026, 8, 23, 9, 17, tzinfo=UTC))
    retry = _incremental_window(datetime(2026, 8, 23, 10, 55, tzinfo=UTC))

    assert first == retry
    assert first == (
        datetime(2026, 8, 23, 0, 0, tzinfo=UTC),
        datetime(2026, 8, 23, 8, 0, tzinfo=UTC),
    )
