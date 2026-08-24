"""The staged classification schema and confidence mapping (B-S14.1 to B-S14.6).

These tests are about what the schema *refuses*. A model that returns an
incoherent answer — a hate label with no type, a severity band on ordinary
discussion — must fail validation rather than have the plausible half of its
answer stored, because the stored half would be a finding nobody made.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    Relevance,
    ReviewTaskType,
    Severity,
    Stance,
)
from amanah.ml.classification import build_model_input
from amanah.ml.confidence import DEFAULT_THRESHOLDS, REVIEW_PRIORITY, review_reason
from amanah.ml.taxonomy import ClassificationOutput


def _output(**overrides: object) -> ClassificationOutput:
    values: dict[str, object] = {
        "relevance": Relevance.muslim_related,
        "stance": Stance.non_hateful_discussion,
        "hate_types": [],
        "severity": Severity.none,
        "narrative_tags": [],
        "score": 0.9,
        "rationale": "Ordinary community discussion.",
        "is_uncertain": False,
    }
    values.update(overrides)
    return ClassificationOutput.model_validate(values)


def test_benign_muslim_content_is_relevant_without_being_hateful() -> None:
    output = _output()

    assert output.relevance is Relevance.muslim_related
    assert output.stance is Stance.non_hateful_discussion
    assert output.hate_types == []
    assert output.severity is Severity.none


def test_counterspeech_is_its_own_stance_and_carries_no_hate_label() -> None:
    output = _output(stance=Stance.counterspeech_or_quotation)

    assert output.stance is Stance.counterspeech_or_quotation
    assert output.hate_types == []


def test_a_hate_label_requires_at_least_one_type() -> None:
    with pytest.raises(ValidationError, match="requires at least one hate type"):
        _output(stance=Stance.likely_anti_muslim, hate_types=[])


def test_a_hate_type_without_the_hate_stance_is_refused() -> None:
    with pytest.raises(ValidationError, match="requires the likely_anti_muslim stance"):
        _output(hate_types=[HateType.derogation])


def test_severity_above_none_without_the_hate_stance_is_refused() -> None:
    with pytest.raises(ValidationError, match="requires the likely_anti_muslim stance"):
        _output(severity=Severity.high)


def test_a_hate_label_on_an_item_the_model_called_unrelated_is_refused() -> None:
    # The numerator would otherwise sit outside its own denominator.
    with pytest.raises(ValidationError, match="requires muslim_related relevance"):
        _output(
            relevance=Relevance.not_related,
            stance=Stance.likely_anti_muslim,
            hate_types=[HateType.derogation],
        )


def test_an_unexpected_field_fails_validation() -> None:
    with pytest.raises(ValidationError):
        ClassificationOutput.model_validate(
            {
                "relevance": "muslim_related",
                "stance": "non_hateful_discussion",
                "score": 0.5,
                "rationale": "",
                "invented_field": "surprise",
            }
        )


def test_a_score_outside_zero_to_one_is_refused() -> None:
    with pytest.raises(ValidationError):
        _output(score=1.4)


def test_narrative_tags_are_bounded_in_count_and_length() -> None:
    with pytest.raises(ValidationError):
        _output(narrative_tags=["a"] * 6)
    with pytest.raises(ValidationError, match="short, non-empty labels"):
        _output(narrative_tags=["x" * 200])


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, ConfidenceTier.low),
        (0.59, ConfidenceTier.low),
        (0.6, ConfidenceTier.medium),
        (0.84, ConfidenceTier.medium),
        (0.85, ConfidenceTier.high),
        (1.0, ConfidenceTier.high),
    ],
)
def test_scores_map_onto_the_documented_tiers(score: float, expected: ConfidenceTier) -> None:
    assert DEFAULT_THRESHOLDS.tier_for(score) is expected


def test_the_default_thresholds_are_marked_provisional() -> None:
    # `rules/ml.md` refuses an accuracy claim without a reviewed evaluation, so
    # the version itself must say the thresholds are uncalibrated (B-S14.4).
    assert "provisional" in DEFAULT_THRESHOLDS.version


def test_an_uncertain_model_routes_to_review_whatever_its_score() -> None:
    reason = review_reason(_output(is_uncertain=True, score=0.99), ConfidenceTier.high)

    assert reason is ReviewTaskType.model_disagreement


def test_unresolved_relevance_routes_to_review() -> None:
    output = _output(relevance=Relevance.uncertain, stance=Stance.uncertain)

    assert review_reason(output, ConfidenceTier.high) is ReviewTaskType.uncertain_relevance


def test_a_severe_claim_routes_to_review_even_at_high_confidence() -> None:
    output = _output(
        stance=Stance.likely_anti_muslim,
        hate_types=[HateType.threat_or_incitement],
        severity=Severity.high,
        score=0.99,
    )

    assert review_reason(output, ConfidenceTier.high) is ReviewTaskType.severity_escalation


def test_a_low_confidence_answer_routes_to_review() -> None:
    assert review_reason(_output(score=0.2), ConfidenceTier.low) is ReviewTaskType.low_confidence


def test_a_confident_ordinary_answer_needs_no_review() -> None:
    assert review_reason(_output(score=0.95), ConfidenceTier.high) is None


def test_every_review_reason_has_a_priority() -> None:
    # A queued task with no priority would sort unpredictably against the rest.
    for task_type in ReviewTaskType:
        assert task_type in REVIEW_PRIORITY


def test_a_dispute_outranks_every_automatic_reason() -> None:
    automatic = max(
        priority
        for task_type, priority in REVIEW_PRIORITY.items()
        if task_type is not ReviewTaskType.dispute
    )

    assert REVIEW_PRIORITY[ReviewTaskType.dispute] > automatic


def test_model_input_carries_context_before_the_item() -> None:
    rendered = build_model_input(
        normalized_text="Actually that is not what the report said.",
        context={"title": "Council debate", "parent_text": "They are all the same."},
    )

    assert rendered.index("Council debate") < rendered.index("Item:")
    assert "In reply to: They are all the same." in rendered
    assert rendered.endswith("Actually that is not what the report said.")


def test_absent_context_fields_are_omitted_rather_than_blanked() -> None:
    rendered = build_model_input(normalized_text="A standalone post.", context={})

    assert rendered == "Item: A standalone post."
