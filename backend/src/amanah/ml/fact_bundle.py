"""Bounded fact bundles: the only thing the narrative layer may see (B-S15.4).

`spec.md` FR-INSIGHT-001 says Gemini receives a bounded structured fact bundle
rather than database access. This module is that bundle, and the shape enforces
three properties the validation step later depends on.

*Every fact has an id.* A citation is a pointer to one of these ids, so a claim
can be checked against the exact figure it came from rather than against a
paragraph.

*Every fact carries its own numbers.* A fact is not a sentence with a number
inside it — it is a value, a numerator, a denominator, and a label. The validator
compares a cited claim against the value, which is only possible because the value
was never flattened into prose.

*The bundle names its own filters.* `filter_hash` is computed from the exact
filters the figures were drawn under, and it is part of the insight cache key. An
insight generated for one window can therefore never be served for another.

Bundles are built from stored buckets and never from a live count, so the facts a
published insight cites stay retrievable exactly as they were.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from amanah.api.schemas.filters import ItemFilters
from amanah.domain.enums import SamplingStratum
from amanah.ml.versions import FACT_BUNDLE_VERSION

#: How many facts one bundle may carry. A bound rather than a preference: the
#: bundle is the model's entire context for the summary, and an unbounded one
#: would blow the input cap and the token budget on the widest filter.
MAX_FACTS = 40

_FIELD_SEPARATOR = "\x00"


@dataclass(frozen=True, slots=True)
class Fact:
    """One citable figure.

    `value` is the number as stated. `numerator` and `denominator` are present
    only for a rate, and when they are, both are present: a rate whose denominator
    travelled separately is exactly the bare percentage `spec.md` section 9.5
    forbids.
    """

    fact_id: str
    label: str
    value: float | int | None
    unit: str
    numerator: int | None = None
    denominator: int | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    sampling_stratum: SamplingStratum | None = None
    note: str | None = None

    def as_prompt_dict(self) -> dict[str, Any]:
        """The fact as the model sees it.

        Absent fields are omitted rather than sent as null, so the model is not
        handed a column of nulls to reason about. Timestamps are dates: the
        summary describes a window, and a microsecond in the prompt is an
        invitation to quote one.
        """
        payload: dict[str, Any] = {
            "id": self.fact_id,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
        }
        if self.numerator is not None and self.denominator is not None:
            payload["numerator"] = self.numerator
            payload["denominator"] = self.denominator
        if self.window_start is not None and self.window_end is not None:
            payload["window"] = {
                "from": self.window_start.date().isoformat(),
                "to": self.window_end.date().isoformat(),
            }
        if self.sampling_stratum is not None:
            payload["sampling_stratum"] = self.sampling_stratum.value
        if self.note is not None:
            payload["note"] = self.note
        return payload


@dataclass(frozen=True, slots=True)
class FactBundle:
    """The complete, immutable input to one narrative generation."""

    filter_hash: str
    data_version: str
    facts: tuple[Fact, ...]
    coverage_warnings: tuple[str, ...] = ()
    methodology_notes: tuple[str, ...] = ()
    sampling_disclosures: tuple[str, ...] = ()
    generated_at: datetime | None = None
    _index: dict[str, Fact] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        if len(self.facts) > MAX_FACTS:
            raise ValueError(f"a bundle may carry at most {MAX_FACTS} facts")
        # Built once so citation validation is a lookup rather than a scan per
        # claim; the bundle is frozen, so the index cannot fall out of date.
        object.__setattr__(self, "_index", {fact.fact_id: fact for fact in self.facts})

    def fact(self, fact_id: str) -> Fact | None:
        """The fact with this id, or `None` if the bundle does not contain it."""
        return self._index.get(fact_id)

    @property
    def fact_ids(self) -> tuple[str, ...]:
        return tuple(fact.fact_id for fact in self.facts)

    @property
    def is_empty(self) -> bool:
        """Whether there is nothing here worth summarising.

        A bundle of facts that are all `None` is not data: it is the shape of
        data. The narrative layer abstains rather than describing an absence as a
        finding.
        """
        return not self.facts or all(fact.value is None for fact in self.facts)

    def render(self) -> str:
        """Serialize the bundle as the model's input.

        JSON rather than prose, because prose is where a number silently becomes
        a claim. The model is a writer over this structure and is told, in the
        prompt, that it may not compute anything not present here.
        """
        return json.dumps(
            {
                "facts": [fact.as_prompt_dict() for fact in self.facts],
                "coverage_warnings": list(self.coverage_warnings),
                "sampling_disclosures": list(self.sampling_disclosures),
                "methodology": list(self.methodology_notes),
            },
            ensure_ascii=False,
            indent=None,
            sort_keys=True,
        )

    def content_hash(self) -> str:
        """A cache key over the exact facts, not merely over the filters.

        Two windows can share a filter hash and hold different data — a re-run
        that ingested more items is the ordinary case. Hashing the rendered facts
        means new data invalidates the cached insight, which is what B-S15.10
        asks for.
        """
        return hashlib.sha256(
            _FIELD_SEPARATOR.join(
                (FACT_BUNDLE_VERSION, self.filter_hash, self.data_version, self.render())
            ).encode("utf-8")
        ).hexdigest()


def filter_hash(filters: ItemFilters) -> str:
    """A stable digest of the filters a bundle was built under.

    Computed from the model's JSON dump with sorted keys, so two requests with the
    same filters in a different query-string order produce the same hash and share
    a cache entry.
    """
    payload = filters.model_dump(mode="json", exclude_none=True)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
