"""Cited narrative summaries over stored facts (B-S15.5, B-S15.7, B-S15.10).

The rule this module enforces is the one that makes AI narrative safe to publish
at all: **a generated claim is checked against the bundle before it is stored.**
The prompt asks the model to cite; this code verifies that it did, that the ids
exist, and that every number in the prose appears in a cited fact. Output that
fails is stored with `validation_status = rejected` and never served.

Verification is numeric rather than semantic. Every number in the generated text
is extracted and matched against the values of the facts the model cited. That
catches the failure that actually matters — a figure the model computed, rounded,
or invented — without pretending to judge whether the sentence around it is a fair
reading. Judging that is what human review is for.

Caching is by fact-bundle hash and by every version that shapes the wording, so
new data invalidates the snapshot rather than being papered over by a stale one.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.metrics import InsightSnapshot
from amanah.domain.enums import PublicPlatform, RetentionPolicy, ValidationStatus
from amanah.ml.catalog import SUMMARIZE_FACTS_PROMPT, SUMMARIZE_FACTS_PROMPT_ID
from amanah.ml.fact_bundle import Fact, FactBundle
from amanah.ml.gemini import GeminiClient, InferenceRequest
from amanah.ml.insight_schema import InsightOutput
from amanah.ml.policy import DataClass, TransferRequest
from amanah.ml.results import InferenceSuccess, failure_reason

logger = logging.getLogger(__name__)

#: Numbers appearing in generated prose: integers, decimals, and percentages,
#: with optional thousands separators.
_NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?%?")

#: Tolerance when matching a quoted figure against a stored value. Wide enough
#: that a rate written as "12%" matches 0.1234, narrow enough that a different
#: number does not.
_RELATIVE_TOLERANCE = 0.01

#: Small integers a sentence can contain without making a quantitative claim
#: about the data — "one of the two windows", "a single day". Requiring a citation
#: for these would reject correct prose over its grammar.
_INCIDENTAL_NUMBERS = frozenset({0.0, 1.0, 2.0})


@dataclass(frozen=True, slots=True)
class InsightResult:
    """The outcome of one insight generation.

    `output` is present only when validation passed. A rejected or unavailable
    insight returns `None` and a reason, and the caller keeps showing the
    deterministic figures — which is `spec.md` FR-INSIGHT-007.
    """

    output: InsightOutput | None
    validation_status: ValidationStatus
    reason: str | None = None
    was_cached: bool = False
    snapshot_id: UUID | None = None


class InsightService:
    """Generates, validates, and caches narrative summaries of stored facts."""

    def __init__(self, session: Session, *, client: GeminiClient) -> None:
        self._session = session
        self._client = client

    def summarize(self, bundle: FactBundle) -> InsightResult:
        """Return a validated summary of this bundle, from cache when possible."""
        if bundle.is_empty:
            return InsightResult(
                output=None,
                validation_status=ValidationStatus.pending,
                reason="insufficient_data",
            )

        cached = self._read_snapshot(bundle)
        if cached is not None:
            return cached

        result = self._client.infer(
            InferenceRequest(
                prompt_id=SUMMARIZE_FACTS_PROMPT_ID,
                content=bundle.render(),
                content_hash=bundle.content_hash(),
                # Aggregates only. The bundle holds counts and rates this product
                # computed; no source text is in it, which is why the summarising
                # prompt is not permitted to receive any.
                transfer=TransferRequest(
                    data_class=DataClass.derived_aggregate,
                    platform=PublicPlatform.not_applicable,
                    retention_policy=RetentionPolicy.indefinite_permitted,
                ),
            ),
            InsightOutput,
        )
        if not isinstance(result, InferenceSuccess):
            reason = failure_reason(result)
            logger.info("insight unavailable", extra={"reason": reason})
            return InsightResult(
                output=None, validation_status=ValidationStatus.pending, reason=reason
            )

        problem = validate_against_bundle(result.payload, bundle)
        status = ValidationStatus.rejected if problem else ValidationStatus.validated
        snapshot_id = self._write_snapshot(bundle, result.payload, status)

        if problem:
            logger.warning("insight failed citation validation", extra={"reason": problem})
            return InsightResult(
                output=None,
                validation_status=status,
                reason=problem,
                snapshot_id=snapshot_id,
            )
        return InsightResult(
            output=result.payload,
            validation_status=status,
            was_cached=result.was_cached,
            snapshot_id=snapshot_id,
        )

    def _read_snapshot(self, bundle: FactBundle) -> InsightResult | None:
        """Return a stored, already-validated snapshot for this exact bundle.

        Only `validated` rows are served. A rejected snapshot is kept as the
        record of a failed generation, not as something to hand back later.
        """
        row = self._session.execute(
            select(InsightSnapshot).where(
                InsightSnapshot.filter_hash == bundle.filter_hash,
                InsightSnapshot.data_version == bundle.content_hash(),
                InsightSnapshot.model_name == self._client.model_name,
                InsightSnapshot.prompt_version == SUMMARIZE_FACTS_PROMPT.version,
                InsightSnapshot.validation_status == ValidationStatus.validated,
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return InsightResult(
            output=InsightOutput.model_validate(row.output),
            validation_status=ValidationStatus.validated,
            was_cached=True,
            snapshot_id=row.id,
        )

    def _write_snapshot(
        self, bundle: FactBundle, output: InsightOutput, status: ValidationStatus
    ) -> UUID:
        """Store the snapshot, converging on re-run rather than duplicating.

        `data_version` holds the bundle's content hash rather than a schema
        version, which is what makes new data a cache miss: the same filters over
        a larger corpus produce a different hash and therefore a new snapshot
        (B-S15.10).
        """
        table = cast(Table, InsightSnapshot.__table__)
        values: dict[str, Any] = {
            "filter_hash": bundle.filter_hash,
            "data_version": bundle.content_hash(),
            "model_name": self._client.model_name,
            "prompt_version": SUMMARIZE_FACTS_PROMPT.version,
            "input_fact_ids": list(bundle.fact_ids),
            "output": output.model_dump(mode="json"),
            "citation_ids": [citation.fact_id for citation in output.citations],
            "validation_status": status.value,
            "generated_at": datetime.now(UTC),
        }
        statement: Any = (
            insert(table)
            .values(**values)
            .on_conflict_do_update(
                constraint="insight_snapshots_filter_data_model_prompt_unique",
                set_={
                    table.c.output: values["output"],
                    table.c.citation_ids: values["citation_ids"],
                    table.c.validation_status: values["validation_status"],
                    table.c.input_fact_ids: values["input_fact_ids"],
                    table.c.generated_at: values["generated_at"],
                },
            )
            .returning(table.c.id)
        )
        return cast(UUID, self._session.execute(statement).scalar_one())


def validate_against_bundle(output: InsightOutput, bundle: FactBundle) -> str | None:
    """Return a safe reason the output must be rejected, or `None` if it holds.

    Three checks, in the order a wrong answer usually fails them: a citation that
    points at nothing, prose that states a figure with no citation at all, and a
    figure that does not match any cited fact.
    """
    for citation in output.citations:
        if bundle.fact(citation.fact_id) is None:
            return "citation_not_in_bundle"

    if output.is_insufficient_data:
        # An abstention is a valid answer. It makes no quantitative claim, so
        # there is nothing further to check.
        return None

    cited = [
        fact for fact in (bundle.fact(c.fact_id) for c in output.citations) if fact is not None
    ]
    for text in _quantitative_text(output):
        numbers = _numbers_in(text)
        if not numbers:
            continue
        if not cited:
            return "quantitative_claim_without_citation"
        for number in numbers:
            if not _matches_any(number, cited):
                return "quantitative_claim_not_in_bundle"
    return None


def _quantitative_text(output: InsightOutput) -> tuple[str, ...]:
    """The fields a numeric claim can appear in.

    `unknowns` is excluded: it describes what the data cannot show, and a
    sentence naming a figure the product does *not* have would be rejected for
    citing a fact that by definition is not in the bundle.
    """
    return (
        output.answer,
        *output.observations,
        *output.interpretation,
        *output.possible_association,
    )


def _numbers_in(text: str) -> tuple[float, ...]:
    """Every figure stated in a piece of generated prose.

    A percentage is converted to its ratio so "12%" and 0.12 compare equal, and
    incidental small integers are dropped so ordinary English does not read as a
    quantitative claim.
    """
    values: list[float] = []
    for match in _NUMBER_PATTERN.finditer(text):
        raw = match.group(0)
        try:
            value = float(raw.rstrip("%").replace(",", ""))
        except ValueError:
            continue
        if raw.endswith("%"):
            value /= 100
        if value not in _INCIDENTAL_NUMBERS:
            values.append(value)
    return tuple(values)


def _matches_any(number: float, facts: list[Fact]) -> bool:
    """Whether a stated figure equals a value, numerator, or denominator cited.

    Numerators and denominators count as matches because a summary may
    legitimately say "142 of 1,900 items", and both halves came from the same
    fact rather than from a calculation the model performed.
    """
    for fact in facts:
        for candidate in (fact.value, fact.numerator, fact.denominator):
            if candidate is None:
                continue
            if _close(number, float(candidate)):
                return True
    return False


def _close(stated: float, stored: float) -> bool:
    """Whether two figures are the same number, allowing for rounding.

    A rate the model wrote as "12%" against a stored 0.1234 is the same claim
    rounded for a reader; a stated 0.5 against a stored 0.12 is a different one.
    """
    if stored == 0:
        return abs(stated) < _RELATIVE_TOLERANCE
    return abs(stated - stored) <= max(_RELATIVE_TOLERANCE, abs(stored) * _RELATIVE_TOLERANCE)
