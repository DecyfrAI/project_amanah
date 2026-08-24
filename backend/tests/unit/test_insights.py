"""Fact bundles, citation fidelity, and causal refusal (B-S15.4 to B-S15.8).

These are the checks that make generated narrative safe to publish. A number the
model computed rather than read, a citation pointing at nothing, or a sentence
asserting that one thing produced another are all rejected here — deterministically
— rather than trusted to a prompt.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from amanah.api.schemas.filters import ItemFilters
from amanah.domain.enums import SamplingStratum
from amanah.metrics.facts import METHODOLOGY_NOTES
from amanah.ml.fact_bundle import MAX_FACTS, Fact, FactBundle, filter_hash
from amanah.ml.insight_schema import InsightCitation, InsightOutput
from amanah.ml.insights import validate_against_bundle

WINDOW_START = datetime(2026, 7, 1, tzinfo=UTC)
WINDOW_END = datetime(2026, 7, 31, tzinfo=UTC)


def _bundle(*facts: Fact, **overrides: object) -> FactBundle:
    values: dict[str, object] = {
        "filter_hash": "f" * 64,
        "data_version": "filters-1",
        "facts": facts
        or (
            Fact(
                fact_id="likely_anti_muslim_rate",
                label="Share of Muslim-related items classified as likely anti-Muslim",
                value=0.12,
                unit="ratio",
                numerator=142,
                denominator=1183,
                window_start=WINDOW_START,
                window_end=WINDOW_END,
            ),
            Fact(
                fact_id="observed_count",
                label="Items observed",
                value=4200,
                unit="items",
            ),
        ),
        "methodology_notes": METHODOLOGY_NOTES,
    }
    values.update(overrides)
    return FactBundle(**values)  # type: ignore[arg-type]


def _output(**overrides: object) -> InsightOutput:
    values: dict[str, object] = {
        "answer": "142 of 1183 Muslim-related items were classified as likely anti-Muslim.",
        "citations": [InsightCitation(fact_id="likely_anti_muslim_rate", statement="the rate")],
    }
    values.update(overrides)
    return InsightOutput.model_validate(values)


# --- Causal language -------------------------------------------------------


@pytest.mark.parametrize(
    "phrasing",
    [
        "The protest caused a rise in the monitored sample.",
        "The rate increased because of the news coverage.",
        "The announcement led to more hostile posts.",
        "Coverage drove the increase that week.",
        "The incident triggered a spike.",
        "The change resulted from the policy debate.",
        "The article sparked a wave of comments.",
        "The debate was responsible for the shift.",
    ],
)
def test_causal_wording_is_rejected_by_the_schema(phrasing: str) -> None:
    with pytest.raises(ValidationError, match="asserts causation"):
        _output(answer=phrasing)


def test_causal_wording_is_rejected_in_every_narrative_field() -> None:
    for field in ("observations", "interpretation", "possible_association", "unknowns"):
        with pytest.raises(ValidationError, match="asserts causation"):
            _output(**{field: ["The rally caused the increase."]})


def test_coincidence_wording_is_permitted() -> None:
    output = _output(
        answer="Coverage of the incident coincides with this window.",
        possible_association=["A news event and the observed change fall in the same week."],
    )

    assert "coincides" in output.answer


def test_ordinary_words_containing_causal_substrings_are_not_rejected() -> None:
    # "increased" contains "cause" as a substring; whole-word matching is what
    # keeps a blunt guard from rejecting correct prose.
    output = _output(answer="The observed count increased to 4200 items.")

    assert "increased" in output.answer


# --- Citation fidelity -----------------------------------------------------


def test_a_grounded_answer_passes_validation() -> None:
    assert validate_against_bundle(_output(), _bundle()) is None


def test_a_citation_pointing_at_nothing_is_rejected() -> None:
    output = _output(citations=[InsightCitation(fact_id="invented_fact", statement="something")])

    assert validate_against_bundle(output, _bundle()) == "citation_not_in_bundle"


def test_a_figure_the_bundle_does_not_hold_is_rejected() -> None:
    output = _output(answer="A total of 9999 items were observed in this window.")

    assert validate_against_bundle(output, _bundle()) == "quantitative_claim_not_in_bundle"


def test_a_figure_with_no_citation_at_all_is_rejected() -> None:
    output = _output(answer="The rate was 12% in this window.", citations=[])

    assert validate_against_bundle(output, _bundle()) == "quantitative_claim_without_citation"


def test_a_rate_quoted_as_a_percentage_matches_its_stored_ratio() -> None:
    output = _output(answer="12% of Muslim-related items carried the label.")

    assert validate_against_bundle(output, _bundle()) is None


def test_a_numerator_and_denominator_both_count_as_grounded() -> None:
    output = _output(answer="That is 142 items out of 1183.")

    assert validate_against_bundle(output, _bundle()) is None


def test_a_computed_figure_is_caught_even_when_derivable() -> None:
    """1183 - 142 = 1041 is arithmetic the model is not permitted to do."""
    output = _output(answer="1041 Muslim-related items carried no hate label.")

    assert validate_against_bundle(output, _bundle()) == "quantitative_claim_not_in_bundle"


def test_thousands_separators_are_understood() -> None:
    output = _output(
        answer="The window covers 4,200 observed items.",
        citations=[InsightCitation(fact_id="observed_count", statement="the observed count")],
    )

    assert validate_against_bundle(output, _bundle()) is None


def test_an_abstention_needs_no_citations() -> None:
    output = _output(
        answer="There is not enough data in this window to summarise.",
        citations=[],
        is_insufficient_data=True,
    )

    assert validate_against_bundle(output, _bundle()) is None


def test_unknowns_may_name_a_figure_the_bundle_lacks() -> None:
    """`unknowns` describes what is missing, so it is not a quantitative claim."""
    output = _output(unknowns=["The sample holds no data for 3 of the days in this window."])

    assert validate_against_bundle(output, _bundle()) is None


# --- Bundle behaviour ------------------------------------------------------


def test_an_empty_bundle_reports_itself_empty() -> None:
    assert _bundle(facts=()).is_empty is True


def test_a_bundle_of_null_values_is_empty() -> None:
    """A shape with no numbers in it is not data to summarise."""
    bundle = _bundle(
        Fact(fact_id="rate", label="rate", value=None, unit="ratio"),
        Fact(fact_id="coverage", label="coverage", value=None, unit="ratio"),
    )

    assert bundle.is_empty is True


def test_a_bundle_is_bounded_in_size() -> None:
    too_many = tuple(
        Fact(fact_id=f"f{index}", label="x", value=index, unit="items")
        for index in range(MAX_FACTS + 1)
    )

    with pytest.raises(ValueError, match="at most"):
        _bundle(*too_many)


def test_the_rendered_bundle_carries_numerator_and_denominator_together() -> None:
    rendered = _bundle().render()

    assert '"numerator": 142' in rendered
    assert '"denominator": 1183' in rendered


def test_the_rendered_bundle_is_stable_across_calls() -> None:
    bundle = _bundle()

    assert bundle.render() == bundle.render()
    assert bundle.content_hash() == bundle.content_hash()


def test_new_data_changes_the_bundle_hash() -> None:
    """B-S15.10: a re-run that ingested more items must miss the cache."""
    before = _bundle(Fact(fact_id="observed_count", label="x", value=100, unit="items"))
    after = _bundle(Fact(fact_id="observed_count", label="x", value=140, unit="items"))

    assert before.content_hash() != after.content_hash()


def test_a_stratum_fact_carries_its_stratum_and_its_warning() -> None:
    bundle = _bundle(
        Fact(
            fact_id="rate.enriched",
            label="rate within the enriched sample",
            value=0.4,
            unit="ratio",
            numerator=4,
            denominator=10,
            sampling_stratum=SamplingStratum.enriched,
            note="This stratum must not be combined with another.",
        )
    )

    payload = bundle.facts[0].as_prompt_dict()
    assert payload["sampling_stratum"] == "enriched"
    assert "must not be combined" in payload["note"]


def test_absent_fields_are_omitted_rather_than_sent_as_null() -> None:
    payload = Fact(fact_id="x", label="x", value=1, unit="items").as_prompt_dict()

    assert "numerator" not in payload
    assert "window" not in payload
    assert "sampling_stratum" not in payload


# --- Filter hashing --------------------------------------------------------


def test_the_same_filters_hash_identically_regardless_of_field_order() -> None:
    first = ItemFilters(country_codes=["GB"], date_from=WINDOW_START, date_to=WINDOW_END)
    second = ItemFilters(date_to=WINDOW_END, date_from=WINDOW_START, country_codes=["GB"])

    assert filter_hash(first) == filter_hash(second)


def test_different_filters_hash_differently() -> None:
    """An insight generated for one window must never be served for another."""
    narrow = ItemFilters(country_codes=["GB"])
    wide = ItemFilters(country_codes=["GB", "US"])

    assert filter_hash(narrow) != filter_hash(wide)


def test_the_methodology_notes_are_citable_and_non_causal() -> None:
    assert METHODOLOGY_NOTES
    for note in METHODOLOGY_NOTES:
        # The notes are handed to the model as citable prose, so they must obey
        # the same rule the output does.
        InsightOutput.model_validate({"answer": "x", "unknowns": [note]})
