"""The one boundary every source crosses (B-S8.1, B-S8.2).

`spec.md` section 10.1 names five responsibilities — discover, fetch,
canonicalize, checkpoint, health-check — and this module is that contract in
types. The point of writing it down is what it forbids: a provider payload never
leaves the adapter that understands it. Everything downstream — normalization,
deduplication, classification, metrics, review — sees `CanonicalContentItem` and
nothing else, so adding a source cannot change how anything after collection
behaves.

Two provenance shapes travel beside the item rather than inside it, because they
answer different questions. `SeedProvenance` records *why this was sampled* and
must survive into methodology, since a purposive sample read as prevalence is
the failure this project most needs to avoid. `DatasetRowProvenance` records
*where a datapack row actually came from*, which the public `N/A` source value
would otherwise erase.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from amanah.domain.enums import (
    ConnectorStatus,
    ContentKind,
    SamplingStratum,
    SourceStatus,
)


@dataclass(frozen=True, slots=True)
class SeedProvenance:
    """Why one approved seed or query was collected from.

    Inclusion in the reviewed registry establishes *sampling relevance*, never a
    hate label, and the stratum must stay attached so an enriched sample is never
    silently pooled into a prevalence claim.
    """

    registry_key: str
    config_version: str
    query_family: str
    query_purpose: str
    sampling_stratum: SamplingStratum
    item_cap: int
    language: str


@dataclass(frozen=True, slots=True)
class DatasetRowProvenance:
    """Where a datapack row came from, kept separate from its public `N/A`."""

    dataset_package_id: Any
    dataset_import_run_id: Any
    dataset_row_id: str


@dataclass(frozen=True, slots=True)
class ContentContext:
    """Bounded, source-aware context assembled for interpretation.

    A comment quoted out of its thread reads very differently from the same
    comment under its parent. None of these fields is required: a missing one
    stays `None` rather than being invented or filled with an empty string, so
    "no parent" and "parent unavailable" remain distinguishable downstream.
    """

    title: str | None = None
    parent_text: str | None = None
    root_text: str | None = None
    caption: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalContentItem:
    """The single shape every adapter and importer produces.

    `original_text` is the permitted source text as retrieved. It is stored
    encrypted and is never published; `permitted_excerpt` is the part licensing
    allows a reader to see. Keeping them separate is what lets the product
    display an excerpt while a researcher's classifier still sees exact wording.
    """

    source_key: str
    source_item_id: str
    content_kind: ContentKind
    observed_at: datetime
    is_fixture: bool

    canonical_url: str | None = None
    title: str | None = None
    permitted_excerpt: str | None = None
    original_text: str | None = None
    publisher_or_container: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    country_code: str | None = None
    geographic_scope: str | None = None
    source_status: SourceStatus = SourceStatus.available
    context: ContentContext = field(default_factory=ContentContext)
    seed: SeedProvenance | None = None
    dataset: DatasetRowProvenance | None = None
    dataset_annotations: Mapping[str, Any] = field(default_factory=dict)
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)
    submitted_origin: Any | None = None


@dataclass(frozen=True, slots=True)
class SourceReference:
    """One item discovery found, in terms only its own adapter understands."""

    reference_id: str
    content_kind: ContentKind
    hint: Mapping[str, Any] = field(default_factory=dict)
    seed: SeedProvenance | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    """The bounds one discovery pass must respect.

    Every field is a limit rather than a preference. An adapter that ignores
    `item_cap` or `window_start` is a bug, not a tuning choice, because these are
    what keep a run bounded against a live provider.
    """

    item_cap: int
    cursor: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """What one discovery pass found, and what it could not reach.

    `coverage_warnings` are publishable sentences about gaps — a feed that was
    unreachable, a video whose comments are disabled. A provider error body never
    goes here; it goes to the logs.
    """

    references: tuple[SourceReference, ...] = ()
    cursor: str | None = None
    coverage_warnings: tuple[str, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FetchedPayload:
    """A provider-shaped payload, still inside the adapter that understands it."""

    reference: SourceReference
    payload: Mapping[str, Any]
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class AdapterCheckpoint:
    """The resume point and coverage a run should persist before continuing."""

    cursor: str | None
    coverage_warnings: tuple[str, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AdapterHealth:
    """Publishable connector state.

    Deliberately coarse. It never distinguishes a bad key from a network failure,
    because that distinction is exactly what an attacker probing `/v1/connections`
    would want.
    """

    status: ConnectorStatus
    safe_warning: str | None = None


class AdapterError(RuntimeError):
    """A failure an adapter already classified for the job state machine.

    `is_retryable` decides whether the stage waits and tries again or dead-letters
    now, and `is_policy_block` separates "we are not allowed to do this" from "it
    did not work". `safe_code` is a stable identifier, never a provider message.
    """

    def __init__(
        self,
        safe_code: str,
        *,
        is_retryable: bool = False,
        is_policy_block: bool = False,
    ) -> None:
        super().__init__(safe_code)
        self.safe_code = safe_code
        self.is_retryable = is_retryable
        self.is_policy_block = is_policy_block


@runtime_checkable
class SourceAdapter(Protocol):
    """What every source implementation must provide.

    `is_fixture` is part of the contract rather than a deployment detail: it
    travels onto every item the adapter produces, so a fixture record stays
    identifiable from storage all the way to the screen and fixtures can never be
    silently substituted for live data.
    """

    @property
    def source_key(self) -> str:
        """Stable configuration key of the source this adapter serves."""

    @property
    def adapter_version(self) -> str:
        """Version recorded on every run and item this adapter produces."""

    @property
    def is_fixture(self) -> bool:
        """Whether this adapter produces synthetic or redacted records."""

    def health_check(self) -> AdapterHealth:
        """Report publishable connector state without contacting a provider."""

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Find at most `request.item_cap` references within the window."""

    def fetch(self, reference: SourceReference) -> FetchedPayload:
        """Retrieve one reference's provider payload."""

    def canonicalize(self, payload: FetchedPayload) -> CanonicalContentItem:
        """Translate one provider payload into the canonical shape."""

    def checkpoint(self, result: DiscoveryResult) -> AdapterCheckpoint:
        """Reduce a discovery pass to the resume point a run should store."""


class BaseSourceAdapter:
    """Shared behaviour so an adapter only writes what is actually different.

    `checkpoint` in particular is the same for every source that paginates by
    cursor, and a per-adapter copy would be a place for one of them to quietly
    stop recording coverage.
    """

    def __init__(self, *, source_key: str, adapter_version: str, is_fixture: bool) -> None:
        self._source_key = source_key
        self._adapter_version = adapter_version
        self._is_fixture = is_fixture

    @property
    def source_key(self) -> str:
        return self._source_key

    @property
    def adapter_version(self) -> str:
        return self._adapter_version

    @property
    def is_fixture(self) -> bool:
        return self._is_fixture

    def health_check(self) -> AdapterHealth:
        return AdapterHealth(status=ConnectorStatus.ok)

    def checkpoint(self, result: DiscoveryResult) -> AdapterCheckpoint:
        return AdapterCheckpoint(
            cursor=result.cursor,
            coverage_warnings=result.coverage_warnings,
            counts=dict(result.counts),
        )


def merge_counts(*sources: Mapping[str, int]) -> dict[str, int]:
    """Add several stage count maps together for a run's `counts` column."""
    merged: dict[str, int] = {}
    for counts in sources:
        for key, value in counts.items():
            merged[key] = merged.get(key, 0) + value
    return merged


def combine_warnings(*groups: Sequence[str]) -> tuple[str, ...]:
    """Collect coverage warnings without repeating an identical sentence."""
    seen: dict[str, None] = {}
    for group in groups:
        for warning in group:
            seen.setdefault(warning, None)
    return tuple(seen)
