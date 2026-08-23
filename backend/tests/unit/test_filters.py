"""Filter and sort validation (B-S2.3, B-S2.6, FR-FILTER-003, FR-FILTER-004)."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from amanah.api.schemas.filters import MAX_FILTER_VALUES, MAX_FILTER_WINDOW, ItemFilters, ItemSort
from amanah.domain.enums import ConfidenceTier, ContentKind, PublicPlatform, Severity

WINDOW_START = datetime(2026, 1, 1, tzinfo=UTC)


def test_empty_filters_are_valid() -> None:
    assert ItemFilters().date_from is None


def test_supported_filters_are_accepted() -> None:
    filters = ItemFilters(
        date_from=WINDOW_START,
        date_to=WINDOW_START + timedelta(days=7),
        content_kinds=[ContentKind.news_article, ContentKind.social_comment],
        platforms=[PublicPlatform.youtube, PublicPlatform.not_applicable],
        dataset_provider="kaggle",
        dataset_name="synthetic-hate-speech",
        dataset_version="1.2.0",
        country_codes=["CA", "GB"],
        narrative_tags=["demographic_replacement"],
        severities=[Severity.moderate, Severity.high],
        confidence_tiers=[ConfidenceTier.high],
    )

    assert filters.platforms == [PublicPlatform.youtube, PublicPlatform.not_applicable]
    assert filters.dataset_provider == "kaggle"


def test_unsupported_filter_field_is_rejected_rather_than_ignored() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ItemFilters(author_name="someone")  # type: ignore[call-arg]

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


def test_unknown_enum_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ItemFilters(content_kinds=["podcast"])  # type: ignore[list-item]


def test_unknown_sort_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="most_severe"):
        ItemSort("most_severe")


def test_supported_sorts_are_stable_and_documented() -> None:
    assert {sort.value for sort in ItemSort} == {
        "newest",
        "oldest",
        "highest_confidence",
        "lowest_confidence",
        "highest_severity",
    }


def test_reversed_date_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ItemFilters(date_from=WINDOW_START, date_to=WINDOW_START - timedelta(days=1))


def test_date_range_beyond_the_maximum_window_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ItemFilters(
            date_from=WINDOW_START,
            date_to=WINDOW_START + MAX_FILTER_WINDOW + timedelta(days=1),
        )


def test_oversized_multi_value_filter_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ItemFilters(country_codes=["CA"] * (MAX_FILTER_VALUES + 1))


@pytest.mark.parametrize("country_code", ["can", "ca", "C1", "CANADA"])
def test_malformed_country_code_is_rejected(country_code: str) -> None:
    with pytest.raises(ValidationError):
        ItemFilters(country_codes=[country_code])


@pytest.mark.parametrize("tag", ["Demographic Replacement", "tag!", "_leading", "trailing_"])
def test_malformed_narrative_tag_is_rejected(tag: str) -> None:
    with pytest.raises(ValidationError):
        ItemFilters(narrative_tags=[tag])


def test_naive_filter_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ItemFilters(date_from=datetime(2026, 1, 1))  # a naive value is the point here
