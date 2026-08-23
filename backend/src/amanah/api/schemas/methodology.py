"""Methodology disclosure contract.

What this discloses is deliberately bounded. A reader learns how the sample was
drawn, what the labels mean, which model and taxonomy versions produced them, and
what the numbers cannot support. A reader does not learn the lexicon, the query
strings, or the seed identifiers: publishing those would tell someone how to
avoid the sampling, and would expose the enriched strata as if they were a
neutral view of a platform.
"""

from pydantic import Field

from amanah.api.schemas.base import ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import ConfidenceTier


class TaxonomyLabel(ResponseModel):
    """One controlled label and what it is defined to mean."""

    key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class ClassificationStageDisclosure(ResponseModel):
    """One stage of the analysis and the labels it may assign.

    Relevance and stance are separate stages. Muslim-related language is never
    hateful by default, and counterspeech or quotation is its own stance.
    """

    stage: str = Field(min_length=1)
    question: str = Field(min_length=1, description="What this stage decides, in plain language.")
    labels: list[TaxonomyLabel] = Field(default_factory=list)


class ConfidenceTierDisclosure(ResponseModel):
    """The versioned score band behind a displayed confidence tier."""

    tier: ConfidenceTier
    minimum_score: float | None = Field(default=None, ge=0.0, le=1.0)
    maximum_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_provisional: bool = Field(
        description="True until the threshold is calibrated against a reviewed holdout set."
    )


class SamplingDisclosure(ResponseModel):
    """How the monitored sample was drawn, and what it therefore is not."""

    summary: str = Field(min_length=1)
    strata: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    prevalence_warning: str = Field(
        min_length=1,
        description="Why this sample cannot be read as a platform-wide or population rate.",
    )


class ModelDisclosure(ResponseModel):
    """Which versions produced the labels currently on display."""

    model_name: str
    model_version: str
    prompt_version: str
    taxonomy_version: str
    is_configured: bool = Field(
        description="False when no classification connector is configured in this environment."
    )


class MethodologyResponse(ResponseModel):
    """`GET /v1/methodology` payload."""

    methodology_version: str = Field(min_length=1)
    last_reviewed_at: UtcDatetime
    sampling: SamplingDisclosure
    classification_stages: list[ClassificationStageDisclosure] = Field(default_factory=list)
    confidence_tiers: list[ConfidenceTierDisclosure] = Field(default_factory=list)
    models: ModelDisclosure
    primary_metric_definition: str = Field(min_length=1)
    coverage_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    meta: ResponseMeta
