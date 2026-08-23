"""The published methodology disclosure.

This is versioned prose, not data, so it lives in code and changes through a
review rather than through a row someone can edit. What it says is bounded on
purpose: it explains how the sample is drawn, what each label means, which
versions produced it, and what the numbers cannot support. It does not publish
the lexicon, the query strings, or the seed identifiers — those would tell
someone how to sit outside the sampling, and would present enriched strata as if
they were a neutral view of a platform.
"""

from __future__ import annotations

from datetime import UTC, datetime

from amanah.api.schemas.common import ResponseMeta
from amanah.api.schemas.methodology import (
    ClassificationStageDisclosure,
    ConfidenceTierDisclosure,
    MethodologyResponse,
    ModelDisclosure,
    SamplingDisclosure,
    TaxonomyLabel,
)
from amanah.domain.enums import ConfidenceTier, HateType, Relevance, Stance
from amanah.settings import Settings

#: Bumped whenever any statement below changes, so a report snapshot can record
#: exactly which methodology it was generated under.
METHODOLOGY_VERSION = "2026.08.1"

LAST_REVIEWED_AT = datetime(2026, 8, 23, tzinfo=UTC)

#: Provisional bands (`spec.md` FR-AI-004). They are explicitly marked
#: provisional until calibrated against a reviewed holdout set; publishing them
#: as settled would be an accuracy claim the project has not earned.
CONFIDENCE_TIERS = (
    ConfidenceTierDisclosure(
        tier=ConfidenceTier.low, minimum_score=None, maximum_score=0.60, is_provisional=True
    ),
    ConfidenceTierDisclosure(
        tier=ConfidenceTier.medium, minimum_score=0.60, maximum_score=0.85, is_provisional=True
    ),
    ConfidenceTierDisclosure(
        tier=ConfidenceTier.high, minimum_score=0.85, maximum_score=None, is_provisional=True
    ),
)

_RELEVANCE_LABELS = (
    TaxonomyLabel(
        key=Relevance.muslim_related.value,
        display_name="Muslim-related",
        definition="The item is about Muslims, Islam, or Muslim communities in some way.",
    ),
    TaxonomyLabel(
        key=Relevance.not_related.value,
        display_name="Not related",
        definition="The item is not about Muslims or Islam.",
    ),
    TaxonomyLabel(
        key=Relevance.uncertain.value,
        display_name="Uncertain",
        definition="There is not enough context to decide, so the item is routed for review.",
    ),
)

_STANCE_LABELS = (
    TaxonomyLabel(
        key=Stance.likely_anti_muslim.value,
        display_name="Likely anti-Muslim",
        definition="The item expresses hostility toward Muslims or Islam.",
    ),
    TaxonomyLabel(
        key=Stance.non_hateful_discussion.value,
        display_name="Non-hateful discussion",
        definition=(
            "The item discusses Muslims or Islam without hostility. Criticism of a "
            "practice, an institution, or a government is not hostility toward people."
        ),
    ),
    TaxonomyLabel(
        key=Stance.counterspeech_or_quotation.value,
        display_name="Counterspeech or quotation",
        definition=(
            "The item quotes, reports, or argues against anti-Muslim speech. It is "
            "recorded separately and is never counted as anti-Muslim rhetoric."
        ),
    ),
    TaxonomyLabel(
        key=Stance.uncertain.value,
        display_name="Uncertain",
        definition="The stance could not be established, so the item is routed for review.",
    ),
)

_HATE_TYPE_DEFINITIONS = {
    HateType.animosity: "General hostility or contempt directed at Muslims.",
    HateType.derogation: "Insulting or demeaning language about Muslims or Islam.",
    HateType.dehumanization: "Language that denies Muslims full human status.",
    HateType.exclusion: "Calls to remove, exclude, or deny rights to Muslims.",
    HateType.threat_or_incitement: "Threats of harm, or encouragement of harm, toward Muslims.",
    HateType.collective_blame: "Holding all Muslims responsible for the acts of individuals.",
    HateType.other: "Anti-Muslim expression that does not fit the categories above.",
}

CLASSIFICATION_STAGES = (
    ClassificationStageDisclosure(
        stage="relevance",
        question="Is this item about Muslims or Islam at all?",
        labels=list(_RELEVANCE_LABELS),
    ),
    ClassificationStageDisclosure(
        stage="stance",
        question="How does the item treat its Muslim-related subject?",
        labels=list(_STANCE_LABELS),
    ),
    ClassificationStageDisclosure(
        stage="hate_type",
        question="If the item is anti-Muslim, what form does it take?",
        labels=[
            TaxonomyLabel(
                key=hate_type.value,
                display_name=hate_type.value.replace("_", " ").capitalize(),
                definition=definition,
            )
            for hate_type, definition in _HATE_TYPE_DEFINITIONS.items()
        ],
    ),
)

SAMPLING = SamplingDisclosure(
    summary=(
        "Items come from reviewed news feeds, approved platform seeds, and reviewed "
        "open datasets. Every seed is approved individually and carries a stated "
        "purpose; nothing is collected because a document mentioned it."
    ),
    strata=[
        "enriched — chosen because anti-Muslim rhetoric is likely to appear there",
        "boundary_control — chosen to test the line between criticism and hostility",
        "ordinary_monitoring — chosen without regard to expected content",
    ],
    languages=["en"],
    prevalence_warning=(
        "The enriched stratum is deliberately over-sampled, so rates computed over "
        "this sample say nothing about how common anti-Muslim speech is on any "
        "platform or among any population. Inclusion of a source means it was "
        "relevant to sample, never that it is hateful."
    ),
)

PRIMARY_METRIC_DEFINITION = (
    "Likely anti-Muslim rhetoric rate in the monitored sample = items labelled "
    "likely anti-Muslim divided by items labelled Muslim-related, over the stated "
    "window and source scope. It is not a measure of public sentiment."
)

COVERAGE_NOTES = (
    "Coverage is the share of observed items that have been analysed. Items awaiting "
    "analysis are counted as observed and excluded from every classification count.",
    "A window with no computed bucket is shown as a gap. Missing data is never rendered as zero.",
    "When collection is stale the last successful data is shown and labelled stale; "
    "fixtures are never substituted for live data.",
)

LIMITATIONS = (
    "Confidence thresholds are provisional and have not been calibrated against a "
    "reviewed holdout set, so no accuracy figure is claimed.",
    "Automated labels are frequently wrong on sarcasm, reclaimed speech, quotation, "
    "and coded language; low-confidence and uncertain items are routed to review and "
    "are never presented as confirmed.",
    "Geography is recorded only when a source states it explicitly, so country "
    "breakdowns undercount rather than estimate.",
    "The sample is English-only for now, which excludes most of the world's Muslim "
    "communities from these figures.",
    "Association between a news event and a change in the metrics is never a causal claim.",
)


def build_methodology(settings: Settings, meta: ResponseMeta) -> MethodologyResponse:
    """Assemble the disclosure for the current environment.

    The model block reflects what is actually configured here: an environment
    with no classification connector says so rather than naming a model that
    never ran.
    """
    gemini = next(
        (connector for connector in settings.connectors if connector.name == "gemini"), None
    )
    is_configured = gemini is not None and gemini.is_configured
    return MethodologyResponse(
        methodology_version=METHODOLOGY_VERSION,
        last_reviewed_at=LAST_REVIEWED_AT,
        sampling=SAMPLING,
        classification_stages=list(CLASSIFICATION_STAGES),
        confidence_tiers=list(CONFIDENCE_TIERS),
        models=ModelDisclosure(
            model_name="gemini",
            # The configured model identifier is a deployment detail, not a
            # secret, but it is only published once it is actually in use.
            model_version=(settings.gemini_model or "not_configured")
            if is_configured
            else "not_configured",
            prompt_version="not_configured" if not is_configured else "v1",
            taxonomy_version=METHODOLOGY_VERSION,
            is_configured=is_configured,
        ),
        primary_metric_definition=PRIMARY_METRIC_DEFINITION,
        coverage_notes=list(COVERAGE_NOTES),
        limitations=list(LIMITATIONS),
        meta=meta,
    )
