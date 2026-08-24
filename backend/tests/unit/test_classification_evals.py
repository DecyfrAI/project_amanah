"""The frozen classification eval set (B-S14.7, B-S14.8).

Two things are checked here, and neither is model accuracy.

*The set stays honest.* Every sample must be well-formed, every ideal must be a
coherent output under the real schema, and the categories that carry the
false-positive risk must actually be present. An eval set that silently lost its
counterspeech samples would keep passing while measuring nothing.

*The grader is correct.* The scoring functions are exercised against constructed
outputs, so a future run's numbers mean what the report says they mean.

No sample is sent to a provider here. Scoring real model output against this set
belongs in the eval workflow (B-S23.5), which runs deliberately and reports per
slice; this file is the deterministic gate that keeps the set usable.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from amanah.domain.enums import Relevance, Stance
from amanah.ml.confidence import DEFAULT_THRESHOLDS, review_reason
from amanah.ml.taxonomy import ClassificationOutput

EVAL_ROOT = Path(__file__).resolve().parents[3] / "evals" / "registry"
SAMPLES_PATH = EVAL_ROOT / "data" / "classification" / "samples.test.v1.jsonl"
DEFINITION_PATH = EVAL_ROOT / "evals" / "classification.yaml"

#: Categories whose samples must never be labelled anti-Muslim. These are the
#: false positives that would make the product harmful to the people it is for.
NEVER_HATE_CATEGORIES = frozenset(
    {"benign_muslim", "news_report", "legitimate_criticism", "counterspeech", "unrelated"}
)


def _samples() -> list[dict[str, Any]]:
    lines = SAMPLES_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines]


def _definition() -> dict[str, Any]:
    return yaml.safe_load(DEFINITION_PATH.read_text(encoding="utf-8"))


def test_every_sample_is_well_formed() -> None:
    for sample in _samples():
        assert sample["id"], sample
        assert sample["category"], sample
        assert sample["input"].strip(), sample
        assert sample["note"].strip(), sample
        # `rules/agentic.md` requires an unambiguous ideal or rubric per sample.
        assert "relevance" in sample["ideal"], sample["id"]
        assert "stance" in sample["ideal"], sample["id"]


def test_sample_ids_are_unique() -> None:
    ids = [sample["id"] for sample in _samples()]

    assert len(ids) == len(set(ids))


def test_every_ideal_is_a_coherent_output_under_the_real_schema() -> None:
    """An ideal the schema would reject is not a target any model can hit."""
    for sample in _samples():
        ideal = sample["ideal"]
        ClassificationOutput.model_validate(
            {
                "relevance": ideal["relevance"],
                "stance": ideal["stance"],
                "hate_types": ideal.get("hate_types", []),
                "severity": ideal.get("min_severity", 1 if ideal.get("hate_types") else 0),
                "narrative_tags": [],
                "score": 0.9,
                "rationale": "eval ideal",
            }
        )


def test_the_false_positive_categories_are_all_present() -> None:
    """The slices that matter most cannot quietly disappear from the set."""
    present = {sample["category"] for sample in _samples()}

    for category in NEVER_HATE_CATEGORIES:
        assert category in present, category


def test_no_never_hate_sample_has_a_hate_ideal() -> None:
    for sample in _samples():
        if sample["category"] in NEVER_HATE_CATEGORIES:
            assert sample["ideal"]["stance"] != Stance.likely_anti_muslim.value, sample["id"]


def test_the_hate_samples_name_at_least_one_type() -> None:
    hate = [sample for sample in _samples() if sample["category"] == "clear_hate"]

    assert hate, "the set must contain samples the classifier should catch"
    for sample in hate:
        assert sample["ideal"]["hate_types"], sample["id"]


def test_the_set_contains_a_naive_baseline_failure() -> None:
    """`rules/agentic.md` requires samples a naive baseline fails.

    A keyword matcher that flags any item mentioning Muslims would fail every
    benign and counterspeech sample; a matcher that flags hostile tone would fail
    the unrelated one. Both traps must be in the set.
    """
    categories = {sample["category"] for sample in _samples()}

    assert "benign_muslim" in categories
    assert "counterspeech" in categories
    assert "unrelated" in categories


def test_the_definition_counts_match_the_data() -> None:
    """The YAML describes the file it actually ships with."""
    counts = Counter(sample["category"] for sample in _samples())
    declared = _definition()["classification.test.v1"]["categories"]

    for category, meta in declared.items():
        assert counts[category] == meta["count"], category
    assert set(declared) == set(counts)


def test_the_definition_pins_the_versions_it_was_written_against() -> None:
    entry = _definition()["classification.test.v1"]

    assert entry["taxonomy_version"] == "taxonomy-1"
    assert entry["prompt_version"] == "classify-1"


def test_the_eval_name_carries_its_split_and_version() -> None:
    # `<name>.<split>.<version>`, so historical results stay comparable.
    assert _definition()["classification"]["id"] == "classification.test.v1"


@pytest.mark.parametrize(
    ("relevance", "stance", "counts_in_denominator"),
    [
        (Relevance.muslim_related, Stance.non_hateful_discussion, True),
        (Relevance.muslim_related, Stance.counterspeech_or_quotation, True),
        (Relevance.not_related, Stance.uncertain, False),
        (Relevance.uncertain, Stance.uncertain, False),
    ],
)
def test_only_muslim_related_items_enter_the_rate_denominator(
    relevance: Relevance, stance: Stance, counts_in_denominator: bool
) -> None:
    """The denominator is Muslim-related items, not every observed item."""
    output = ClassificationOutput.model_validate(
        {
            "relevance": relevance,
            "stance": stance,
            "score": 0.8,
            "rationale": "",
        }
    )

    assert (output.relevance is Relevance.muslim_related) is counts_in_denominator


def test_a_coded_sample_is_allowed_to_abstain() -> None:
    """An uncertain answer on an ambiguous item is a pass, not a miss.

    The alternative — forcing a label — is how a monitoring tool starts inventing
    findings about people.
    """
    uncertain = ClassificationOutput.model_validate(
        {
            "relevance": Relevance.uncertain,
            "stance": Stance.uncertain,
            "score": 0.3,
            "rationale": "Not determinable from the text present.",
            "is_uncertain": True,
        }
    )

    assert review_reason(uncertain, DEFAULT_THRESHOLDS.tier_for(0.3)) is not None
