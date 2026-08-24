"""Structured narrative output over a fact bundle (B-S15.5, B-S15.6).

The fields exist to keep four different kinds of statement from blending into one
paragraph. `observations` is what the stored facts say. `interpretation` is what a
reader might take from that. `possible_association` is co-occurrence and nothing
stronger. `unknowns` is what the data cannot answer. A single free-text summary
would let the model slide from the first to the second without a reader noticing,
which `spec.md` section 9.4 forbids.

Causal wording is rejected here, not merely discouraged in the prompt. A prompt is
an instruction; this is a gate. `rules/agentic.md` §5 prefers a deterministic
check over trusting the model, and the check runs on every field before the
output can be cached or published.
"""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_STATEMENTS = 6
MAX_STATEMENT_LENGTH = 400
MAX_ANSWER_LENGTH = 1200

#: Wording that asserts one thing produced another. Matched on whole words so
#: "increased" does not trip "caused", and applied to every narrative field.
#: Deliberately blunt: a false positive costs one regenerated sentence, while a
#: false negative publishes a causal claim this data cannot support.
CAUSAL_PATTERN = re.compile(
    r"\b("
    r"caused?|causing|causes|because|due to|led to|leads? to|leading to|"
    r"drove|driven by|drives?|driving|triggered?|triggering|triggers|"
    r"sparked?|sparking|sparks|resulted? (?:in|from)|resulting (?:in|from)|"
    r"as a result of|consequence of|responsible for|blamed? on|"
    r"provoked?|provoking|prompted|prompting|fueled|fuelled|fuelling|fueling"
    r")\b",
    re.IGNORECASE,
)


class InsightCitation(BaseModel):
    """A pointer to one fact in the bundle that was supplied."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1, max_length=120)
    statement: str = Field(
        max_length=MAX_STATEMENT_LENGTH,
        description="The claim this citation supports, in the model's own words.",
    )


def reject_causal_language(value: str, field: str) -> str:
    """Raise when a narrative field asserts causation."""
    match = CAUSAL_PATTERN.search(value)
    if match is not None:
        raise ValueError(f"{field} asserts causation: {match.group(0)!r}")
    return value


class InsightOutput(BaseModel):
    """A cited narrative summary of a bundle of stored facts."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(max_length=MAX_ANSWER_LENGTH)
    observations: list[str] = Field(
        default_factory=list,
        max_length=MAX_STATEMENTS,
        description="What the supplied facts state, without interpretation.",
    )
    interpretation: list[str] = Field(
        default_factory=list,
        max_length=MAX_STATEMENTS,
        description="What a reader might take from the observations, marked as such.",
    )
    possible_association: list[str] = Field(
        default_factory=list,
        max_length=MAX_STATEMENTS,
        description="Co-occurrence in the window. Never a causal claim.",
    )
    unknowns: list[str] = Field(
        default_factory=list,
        max_length=MAX_STATEMENTS,
        description="What this data cannot answer.",
    )
    citations: list[InsightCitation] = Field(default_factory=list)
    is_insufficient_data: bool = Field(
        default=False,
        description="Set when the bundle is too thin to summarise honestly.",
    )

    @model_validator(mode="after")
    def _check_language(self) -> Self:
        reject_causal_language(self.answer, "answer")
        for field, values in (
            ("observations", self.observations),
            ("interpretation", self.interpretation),
            ("possible_association", self.possible_association),
            ("unknowns", self.unknowns),
        ):
            for value in values:
                if len(value) > MAX_STATEMENT_LENGTH:
                    raise ValueError(f"{field} entry exceeds the length limit")
                reject_causal_language(value, field)
        return self
