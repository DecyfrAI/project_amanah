"""The deterministic fixture adapter (B-S8.3, B-S8.4, B-S8.7).

This adapter is the reference implementation of the contract and the only one
that can run with no credentials, no network, and no provider. That makes it the
thing every other adapter is checked against: the contract test suite runs
against it, and an end-to-end run through it proves the pipeline is idempotent
without touching anyone's servers.

Two properties matter beyond convenience. It is **deterministic** — the same
fixture file produces the same references, the same canonical items, and the same
hashes on every run, so "the pipeline changed" and "the data changed" stay
distinguishable. And it is **honest**: every record it produces carries
`is_fixture=True` from here through storage to the API, so fixture data can never
be presented as live collection.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

from amanah.domain.enums import ContentKind, SourceStatus
from amanah.ingestion.contract import (
    AdapterError,
    BaseSourceAdapter,
    CanonicalContentItem,
    ContentContext,
    DiscoveryRequest,
    DiscoveryResult,
    FetchedPayload,
    SourceReference,
)

#: Ships inside the package, so a deployed artifact can run the fixture pipeline
#: without the repository being present.
FIXTURE_PATH = Path(__file__).resolve().parent / "data" / "collection_fixtures.json"

#: The configuration key of the fixture source in `config/sources.example.yml`.
FIXTURE_SOURCE_KEY = "fixtures"

ADAPTER_VERSION = "fixtures-1.0.0"


class FixtureAdapter(BaseSourceAdapter):
    """Serves canonical items from a committed synthetic corpus."""

    def __init__(self, fixture_path: Path | None = None) -> None:
        super().__init__(
            source_key=FIXTURE_SOURCE_KEY,
            adapter_version=ADAPTER_VERSION,
            is_fixture=True,
        )
        self._fixture_path = fixture_path or FIXTURE_PATH

    @cached_property
    def _records(self) -> dict[str, dict[str, Any]]:
        """Load the corpus once, keyed by reference."""
        try:
            document = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AdapterError("fixture_corpus_unreadable") from exc
        return {record["reference_id"]: record for record in document["items"]}

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Return references in file order, respecting the window and the cap.

        The cursor is the last reference returned, so resuming is exact rather
        than positional: inserting a record into the corpus cannot make a resumed
        run skip or repeat one.
        """
        ordered = list(self._records.values())
        if request.cursor is not None:
            keys = [record["reference_id"] for record in ordered]
            if request.cursor not in keys:
                raise AdapterError("fixture_cursor_unknown")
            ordered = ordered[keys.index(request.cursor) + 1 :]

        selected: list[SourceReference] = []
        skipped_by_window = 0
        for record in ordered:
            published = _parse_time(record.get("published_at"))
            if _outside_window(published, request):
                skipped_by_window += 1
                continue
            selected.append(
                SourceReference(
                    reference_id=record["reference_id"],
                    content_kind=ContentKind(record["content_kind"]),
                )
            )
            if len(selected) >= request.item_cap:
                break

        remaining = len(ordered) - skipped_by_window - len(selected)
        warnings: tuple[str, ...] = ()
        if remaining > 0:
            # A capped run is a partial view of the window, and the reader is
            # told so rather than being shown a total that looks complete.
            warnings = (
                "The item cap was reached before the window was exhausted, "
                "so this run covers part of the window only.",
            )
        return DiscoveryResult(
            references=tuple(selected),
            cursor=selected[-1].reference_id if selected else request.cursor,
            coverage_warnings=warnings,
            counts={"discovered": len(selected), "skipped_out_of_window": skipped_by_window},
        )

    def fetch(self, reference: SourceReference) -> FetchedPayload:
        record = self._records.get(reference.reference_id)
        if record is None:
            raise AdapterError("fixture_reference_missing")
        return FetchedPayload(
            reference=reference,
            payload=record,
            # Fixed rather than `now()`: an observation time that moves every run
            # would make the corpus non-deterministic for no benefit.
            retrieved_at=_parse_time(record["published_at"]) or datetime.now(UTC),
        )

    def canonicalize(self, payload: FetchedPayload) -> CanonicalContentItem:
        record = payload.payload
        return CanonicalContentItem(
            source_key=self.source_key,
            source_item_id=str(record["reference_id"]),
            content_kind=ContentKind(record["content_kind"]),
            observed_at=payload.retrieved_at,
            is_fixture=True,
            canonical_url=record.get("canonical_url"),
            title=record.get("title"),
            permitted_excerpt=record.get("permitted_excerpt"),
            original_text=record.get("original_text"),
            publisher_or_container=record.get("publisher_or_container"),
            published_at=_parse_time(record.get("published_at")),
            language=record.get("language"),
            country_code=record.get("country_code"),
            geographic_scope=record.get("geographic_scope"),
            source_status=SourceStatus(record.get("source_status", SourceStatus.available.value)),
            context=ContentContext(
                title=record.get("title"),
                parent_text=record.get("parent_text"),
                root_text=record.get("root_text"),
                caption=record.get("caption"),
            ),
        )


def _parse_time(value: object) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _outside_window(published: datetime | None, request: DiscoveryRequest) -> bool:
    """Whether a record falls outside the requested window.

    A record with no publication time is kept: excluding it would silently drop
    items for lacking a field, which is a different decision from the one the
    window expresses.
    """
    if published is None:
        return False
    if request.window_start is not None and published < request.window_start:
        return True
    return request.window_end is not None and published > request.window_end
