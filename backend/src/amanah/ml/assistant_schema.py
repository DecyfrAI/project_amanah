"""Structured output of the grounded dashboard assistant (B-S25.4).

Mirrors the frontend `AssistantReply` contract in
`apps/web/src/api/contracts.ts`: an answer, typed citations, limitations, and a
`grounded_in` value that tells the reader what the answer actually rests on.

`grounded_in: none` is the abstention. It is a normal, expected outcome rather
than an error — a question the stored facts cannot answer gets a plain "the
dashboard does not hold that" instead of a plausible sentence, which is the whole
reason this endpoint routes through a schema at all.

Causal language is rejected by the same deterministic check the insight schema
uses, so the assistant and the cached insights cannot disagree about what counts
as a causal claim.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from amanah.ml.insight_schema import MAX_STATEMENTS, reject_causal_language

MAX_ANSWER_LENGTH = 1200
MAX_LIMITATION_LENGTH = 300
MAX_CITATIONS = 8


class GroundedIn(StrEnum):
    """What the answer rests on."""

    figures = "figures"
    methodology = "methodology"
    none = "none"


class CitationKind(StrEnum):
    """The three kinds of material the assistant is allowed to cite."""

    metric = "metric"
    coverage = "coverage"
    methodology = "methodology"


class AssistantCitation(BaseModel):
    """One pointer into the supplied material."""

    model_config = ConfigDict(extra="forbid")

    kind: CitationKind
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=200)


class AssistantOutput(BaseModel):
    """The model's answer, before citations are verified against the bundle."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=MAX_ANSWER_LENGTH)
    citations: list[AssistantCitation] = Field(default_factory=list, max_length=MAX_CITATIONS)
    limitations: list[str] = Field(default_factory=list, max_length=MAX_STATEMENTS)
    grounded_in: GroundedIn

    @model_validator(mode="after")
    def _check_answer(self) -> Self:
        reject_causal_language(self.answer, "answer")
        for limitation in self.limitations:
            if len(limitation) > MAX_LIMITATION_LENGTH:
                raise ValueError("limitation exceeds the length limit")
            reject_causal_language(limitation, "limitations")
        if self.grounded_in is GroundedIn.none and self.citations:
            # An ungrounded answer that cites something is claiming support it
            # just said it does not have.
            raise ValueError("an ungrounded answer must not cite facts")
        return self
