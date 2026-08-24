"""Schedule-safe ETL dispatch validation and redacted run artifacts."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from amanah.ingestion.configuration import SeedConfiguration, SourceConfiguration

MAX_SCHEDULED_ITEMS = 1_000


class EtlValidationError(ValueError):
    """A dispatch input is broader than reviewed configuration permits."""


@dataclass(frozen=True, slots=True)
class EtlDispatch:
    sources: tuple[str, ...]
    item_cap: int
    registry_keys: tuple[str, ...] = ()
    config_version: str | None = None
    dry_run: bool = False
    datapack_ids: tuple[str, ...] = ()


class ApprovedDatapack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_id: str = Field(min_length=1, max_length=100)
    manifest_path: Path
    data_path: Path
    is_enabled: bool = False


class DatapackConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    config_version: str = Field(min_length=1, max_length=50)
    packages: tuple[ApprovedDatapack, ...] = ()

    def by_id(self, manifest_id: str) -> ApprovedDatapack | None:
        return next(
            (package for package in self.packages if package.manifest_id == manifest_id), None
        )


@dataclass(frozen=True, slots=True)
class RedactedRunSummary:
    source: str
    status: str
    started_at: str
    completed_at: str
    counts: dict[str, int]
    coverage_warnings: tuple[str, ...] = ()
    safe_error_codes: tuple[str, ...] = ()
    run_id: str | None = None


def validate_dispatch(
    dispatch: EtlDispatch,
    *,
    sources: SourceConfiguration,
    seeds: SeedConfiguration,
    datapacks: DatapackConfiguration | None = None,
) -> EtlDispatch:
    """Allow only enabled source keys and approved seed identities."""
    if sources.config_version != seeds.config_version:
        raise EtlValidationError("source and seed config versions do not match")
    if datapacks is not None and datapacks.config_version != sources.config_version:
        raise EtlValidationError("datapack and source config versions do not match")
    if not dispatch.sources:
        raise EtlValidationError("at least one configured source is required")
    if dispatch.item_cap < 1 or dispatch.item_cap > MAX_SCHEDULED_ITEMS:
        raise EtlValidationError(f"item cap must be between 1 and {MAX_SCHEDULED_ITEMS}")
    configured = {entry.source_key: entry for entry in sources.sources}
    for source_key in dispatch.sources:
        source = configured.get(source_key)
        if source is None:
            raise EtlValidationError("source is not present in reviewed configuration")
        if not source.is_enabled:
            raise EtlValidationError("source is disabled in reviewed configuration")
    if dispatch.registry_keys:
        if dispatch.config_version != seeds.config_version:
            raise EtlValidationError("seed config version does not match the reviewed version")
        for registry_key in dispatch.registry_keys:
            seed = seeds.by_registry_key(registry_key)
            if seed is None or not seed.is_runnable:
                raise EtlValidationError("seed key is not approved and runnable")
            if seed.source_key not in dispatch.sources:
                raise EtlValidationError("seed key does not belong to a selected source")
    if dispatch.datapack_ids:
        if datapacks is None:
            raise EtlValidationError("datapack configuration is unavailable")
        for manifest_id in dispatch.datapack_ids:
            package = datapacks.by_id(manifest_id)
            if package is None or not package.is_enabled:
                raise EtlValidationError("datapack manifest ID is not approved and enabled")
    return dispatch


def dispatch_from_environment(environment: Mapping[str, str] | None = None) -> EtlDispatch:
    """Parse the narrow environment contract used by scheduled/manual workflows."""
    values = os.environ if environment is None else environment
    source_text = values.get("ETL_SOURCES", "")
    sources = tuple(dict.fromkeys(part.strip() for part in source_text.split(",") if part.strip()))
    key_text = values.get("ETL_REGISTRY_KEYS", "")
    registry_keys = tuple(
        dict.fromkeys(part.strip() for part in key_text.split(",") if part.strip())
    )
    datapack_text = values.get("ETL_DATAPACK_IDS", "")
    datapack_ids = tuple(
        dict.fromkeys(part.strip() for part in datapack_text.split(",") if part.strip())
    )
    try:
        item_cap = int(values.get("ETL_MAX_ITEMS", "100"))
    except ValueError as exc:
        raise EtlValidationError("ETL_MAX_ITEMS must be an integer") from exc
    return EtlDispatch(
        sources=sources,
        item_cap=item_cap,
        registry_keys=registry_keys,
        config_version=values.get("ETL_CONFIG_VERSION") or None,
        dry_run=values.get("ETL_DRY_RUN", "false").casefold() == "true",
        datapack_ids=datapack_ids,
    )


def load_datapack_configuration(directory: Path) -> DatapackConfiguration:
    """Load the reviewed manifest-ID allowlist; paths remain repository-relative."""
    path = directory / "datapacks.example.yml"
    if not path.is_file():
        raise EtlValidationError("reviewed datapack configuration is missing")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DatapackConfiguration.model_validate(document)


def resolve_approved_datapack(
    package: ApprovedDatapack, *, repository_root: Path
) -> tuple[Path, Path]:
    """Resolve reviewed relative paths and prevent traversal outside the repository."""
    root = repository_root.resolve()
    manifest = (root / package.manifest_path).resolve()
    data = (root / package.data_path).resolve()
    if root not in manifest.parents or root not in data.parents:
        raise EtlValidationError("datapack paths must stay inside the repository")
    return manifest, data


def write_redacted_summary(path: Path, summaries: tuple[RedactedRunSummary, ...]) -> None:
    """Write only identifiers, counts, warnings, and safe codes to an artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "runs": [asdict(summary) for summary in summaries],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
