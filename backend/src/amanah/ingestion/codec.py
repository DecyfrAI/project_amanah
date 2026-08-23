"""Serializing a canonical item across a job boundary.

Between two stages the only carrier is a JSONB column, so a `CanonicalContentItem`
has to survive a round trip through JSON without losing type. That is what this
module does, and it does nothing else — no defaulting, no coercion of unusable
values into plausible ones. A payload that does not decode is an error, because
the alternative is a stage quietly processing an item that is not the one the
previous stage produced.

Timestamps go out as ISO-8601 with an explicit offset and come back timezone
aware. `None` survives as `None`: an absent published time is not "now".
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from amanah.domain.enums import ContentKind, SamplingStratum, SourceStatus
from amanah.ingestion.contract import (
    CanonicalContentItem,
    ContentContext,
    DatasetRowProvenance,
    SeedProvenance,
    SourceReference,
)


class PayloadDecodeError(ValueError):
    """A stored stage payload is not a value this stage can act on."""


def _encode_time(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value is not None else None


def _decode_time(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise PayloadDecodeError("timestamp is not ISO-8601") from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _encode_seed(seed: SeedProvenance | None) -> dict[str, Any] | None:
    if seed is None:
        return None
    return {
        "registry_key": seed.registry_key,
        "config_version": seed.config_version,
        "query_family": seed.query_family,
        "query_purpose": seed.query_purpose,
        "sampling_stratum": seed.sampling_stratum.value,
        "item_cap": seed.item_cap,
        "language": seed.language,
    }


def _decode_seed(raw: object) -> SeedProvenance | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise PayloadDecodeError("seed provenance is not a mapping")
    try:
        return SeedProvenance(
            registry_key=str(raw["registry_key"]),
            config_version=str(raw["config_version"]),
            query_family=str(raw["query_family"]),
            query_purpose=str(raw["query_purpose"]),
            sampling_stratum=SamplingStratum(raw["sampling_stratum"]),
            item_cap=int(raw["item_cap"]),
            language=str(raw["language"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PayloadDecodeError("seed provenance is incomplete") from exc


def encode_reference(reference: SourceReference) -> dict[str, Any]:
    """Serialize one discovered reference for the `fetch` stage."""
    return {
        "reference_id": reference.reference_id,
        "content_kind": reference.content_kind.value,
        "hint": dict(reference.hint),
        "seed": _encode_seed(reference.seed),
    }


def decode_reference(raw: Mapping[str, Any]) -> SourceReference:
    """Recover a discovered reference, or refuse."""
    try:
        return SourceReference(
            reference_id=str(raw["reference_id"]),
            content_kind=ContentKind(raw["content_kind"]),
            hint=dict(raw.get("hint") or {}),
            seed=_decode_seed(raw.get("seed")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PayloadDecodeError("reference payload is incomplete") from exc


def encode_item(item: CanonicalContentItem) -> dict[str, Any]:
    """Serialize one canonical item for the `normalize` stage."""
    return {
        "source_key": item.source_key,
        "source_item_id": item.source_item_id,
        "content_kind": item.content_kind.value,
        "observed_at": _encode_time(item.observed_at),
        "is_fixture": item.is_fixture,
        "canonical_url": item.canonical_url,
        "title": item.title,
        "permitted_excerpt": item.permitted_excerpt,
        "original_text": item.original_text,
        "publisher_or_container": item.publisher_or_container,
        "published_at": _encode_time(item.published_at),
        "language": item.language,
        "country_code": item.country_code,
        "geographic_scope": item.geographic_scope,
        "source_status": item.source_status.value,
        "context": {
            "title": item.context.title,
            "parent_text": item.context.parent_text,
            "root_text": item.context.root_text,
            "caption": item.context.caption,
        },
        "seed": _encode_seed(item.seed),
        "dataset": (
            {
                "dataset_package_id": str(item.dataset.dataset_package_id),
                "dataset_import_run_id": str(item.dataset.dataset_import_run_id),
                "dataset_row_id": item.dataset.dataset_row_id,
            }
            if item.dataset is not None
            else None
        ),
        "dataset_annotations": dict(item.dataset_annotations),
        "provider_metadata": dict(item.provider_metadata),
        "submitted_origin": str(item.submitted_origin) if item.submitted_origin else None,
    }


def decode_item(raw: Mapping[str, Any]) -> CanonicalContentItem:
    """Recover a canonical item, or refuse."""
    try:
        observed_at = _decode_time(raw["observed_at"])
        if observed_at is None:
            raise PayloadDecodeError("canonical item has no observation time")
        context = raw.get("context") or {}
        dataset = raw.get("dataset")
        return CanonicalContentItem(
            source_key=str(raw["source_key"]),
            source_item_id=str(raw["source_item_id"]),
            content_kind=ContentKind(raw["content_kind"]),
            observed_at=observed_at,
            is_fixture=bool(raw["is_fixture"]),
            canonical_url=raw.get("canonical_url"),
            title=raw.get("title"),
            permitted_excerpt=raw.get("permitted_excerpt"),
            original_text=raw.get("original_text"),
            publisher_or_container=raw.get("publisher_or_container"),
            published_at=_decode_time(raw.get("published_at")),
            language=raw.get("language"),
            country_code=raw.get("country_code"),
            geographic_scope=raw.get("geographic_scope"),
            source_status=SourceStatus(raw.get("source_status", SourceStatus.available.value)),
            context=ContentContext(
                title=context.get("title"),
                parent_text=context.get("parent_text"),
                root_text=context.get("root_text"),
                caption=context.get("caption"),
            ),
            seed=_decode_seed(raw.get("seed")),
            dataset=(
                DatasetRowProvenance(
                    dataset_package_id=UUID(str(dataset["dataset_package_id"])),
                    dataset_import_run_id=UUID(str(dataset["dataset_import_run_id"])),
                    dataset_row_id=str(dataset["dataset_row_id"]),
                )
                if dataset is not None
                else None
            ),
            dataset_annotations=dict(raw.get("dataset_annotations") or {}),
            provider_metadata=dict(raw.get("provider_metadata") or {}),
            submitted_origin=(
                UUID(str(raw["submitted_origin"])) if raw.get("submitted_origin") else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PayloadDecodeError("canonical item payload is incomplete") from exc
