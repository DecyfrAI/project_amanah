"""The structured output one classification produces (B-S14.1, B-S14.2).

The stages are separate fields rather than one label because conflating them is
the specific harm this product is built to avoid. `relevance` asks whether an item
is about Muslims or Islam; `stance` asks how it treats that subject. Keeping them
apart is what stops "mentions Islam" from becoming "anti-Muslim", and it is why a
mosque announcement, a news report, a theological critique, and a slur are four
different outputs rather than four points on one scale.

`counterspeech_or_quotation` is a first-class stance for the same reason. Someone
quoting a slur to condemn it uses the same words as someone using it, and a model
that cannot say which is happening will report anti-Muslim rhetoric wherever
people are objecting to it.

Validation lives in the model. A payload that claims `severity` above zero while
reporting a non-hateful stance is rejected here, so an incoherent answer becomes
`invalid_output` and reaches a human instead of a chart.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from amanah.domain.enums import HateType, Relevance, Severity, Stance

#: Narrative tags are a free vocabulary, so they are bounded by count and length
#: rather than by an enum. Unbounded model-authored strings would otherwise reach
#: a filter dropdown and a report.
MAX_NARRATIVE_TAGS = 5
MAX_NARRATIVE_TAG_LENGTH = 60

#: A rationale explains the label. It is not a place to restate the item, and the
#: bound is what stops a model from returning the source text as its reasoning.
MAX_RATIONALE_LENGTH = 400


class ClassificationOutput(BaseModel):
    """One staged classification, as the model must return it.

    `extra="forbid"` so a model that invents a field fails validation instead of
    having it silently dropped: an unexpected key means the output was produced
    against a different understanding of the schema than this one.
    """

    model_config = ConfigDict(extra="forbid")

    relevance: Relevance = Field(
        description="Whether the item is about Muslims or Islam at all.",
    )
    stance: Stance = Field(
        description="How the item treats its Muslim-related subject.",
    )
    hate_types: list[HateType] = Field(
        default_factory=list,
        description="Taxonomy labels. Empty unless the stance is likely_anti_muslim.",
    )
    severity: Severity = Field(
        default=Severity.none,
        description="Harm band; none unless the stance is likely_anti_muslim.",
    )
    narrative_tags: list[str] = Field(
        default_factory=list,
        max_length=MAX_NARRATIVE_TAGS,
        description="Short recurring-theme labels describing the framing.",
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence that the stance label is correct.",
    )
    rationale: str = Field(
        max_length=MAX_RATIONALE_LENGTH,
        description="One or two sentences explaining the label. Never a copy of the item.",
    )
    is_uncertain: bool = Field(
        default=False,
        description="Set when the item is genuinely ambiguous and needs a human.",
    )

    @model_validator(mode="after")
    def _check_coherent(self) -> Self:
        """Refuse an answer whose parts contradict each other.

        A label that only a human could reconcile is not a usable finding, and
        silently keeping the parts that look plausible would publish half of an
        answer the model did not actually give.
        """
        is_hate = self.stance is Stance.likely_anti_muslim
        if not is_hate and self.hate_types:
            raise ValueError("hate_types requires the likely_anti_muslim stance")
        if not is_hate and self.severity is not Severity.none:
            raise ValueError("severity above none requires the likely_anti_muslim stance")
        if is_hate and not self.hate_types:
            raise ValueError("likely_anti_muslim requires at least one hate type")
        if is_hate and self.relevance is not Relevance.muslim_related:
            # The rate's denominator is Muslim-related items. A hate label on an
            # item the model itself called unrelated would put a numerator
            # outside its own denominator.
            raise ValueError("likely_anti_muslim requires muslim_related relevance")
        for tag in self.narrative_tags:
            if not tag.strip() or len(tag) > MAX_NARRATIVE_TAG_LENGTH:
                raise ValueError("narrative tags must be short, non-empty labels")
        return self
