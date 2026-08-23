"""Authenticated-safe item, dashboard, and resource projections (B-S2.2, B-S2.7)."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from amanah.api.schemas.common import CoverageSummary, MetricRate, ResponseMeta
from amanah.api.schemas.dashboard import (
    DashboardMetrics,
    DashboardResponse,
    DashboardTrend,
    HeadlineCard,
    TrendPoint,
)
from amanah.api.schemas.items import DatasetProvenance, ItemDetail, ItemSummary
from amanah.api.schemas.resources import ResourceEntry
from amanah.domain.enums import (
    NOT_APPLICABLE_DISPLAY,
    ConfidenceTier,
    ContentKind,
    DataMode,
    HateType,
    MetricInterval,
    PublicPlatform,
    Relevance,
    ResourceCategory,
    ReviewState,
    Severity,
    SourceStatus,
    Stance,
)

OBSERVED_AT = datetime(2026, 1, 8, tzinfo=UTC)
WINDOW_START = datetime(2026, 1, 1, tzinfo=UTC)


def make_item_summary(**overrides: Any) -> ItemSummary:
    values: dict[str, Any] = {
        "id": uuid4(),
        "content_kind": ContentKind.social_comment,
        "platform": PublicPlatform.youtube,
        "title": "Synthetic fixture comment",
        "permitted_excerpt": "Redacted synthetic excerpt.",
        "publisher_or_container": "Synthetic channel",
        "canonical_url": "https://example.test/watch",
        "published_at": OBSERVED_AT,
        "observed_at": OBSERVED_AT,
        "language": "en",
        "country_code": "CA",
        "source_status": SourceStatus.available,
        "is_fixture": True,
        "relevance": Relevance.muslim_related,
        "stance": Stance.counterspeech_or_quotation,
        "hate_types": [],
        "severity": Severity.none,
        "confidence_tier": ConfidenceTier.medium,
        "review_state": ReviewState.model_only,
        "requires_review": False,
    }
    values.update(overrides)
    return ItemSummary(**values)


def summary_fields(**overrides: Any) -> dict[str, Any]:
    """Field values of a summary, without the computed display field."""
    return make_item_summary(**overrides).model_dump(exclude={"platform_display"})


def make_rate() -> MetricRate:
    return MetricRate(
        numerator=2,
        denominator=10,
        window_start=WINDOW_START,
        window_end=OBSERVED_AT,
        source_scope=["fixtures"],
        data_mode=DataMode.fixture,
    )


def test_item_summary_exposes_no_author_or_raw_content_fields() -> None:
    forbidden = {
        "author",
        "author_id",
        "author_name",
        "raw_text",
        "text_ciphertext",
        "normalized_text",
        "raw_object_key",
    }

    assert forbidden.isdisjoint(ItemDetail.model_fields)


def test_open_datapack_item_displays_not_applicable_but_keeps_dataset_lineage() -> None:
    item = make_item_summary(
        content_kind=ContentKind.dataset_record,
        platform=PublicPlatform.not_applicable,
        canonical_url=None,
        dataset=DatasetProvenance(
            provider="kaggle",
            name="synthetic-hate-speech",
            version="1.2.0",
            license_id="CC-BY-4.0",
            landing_page_url="https://example.test/dataset",
        ),
    )

    assert item.platform_display == NOT_APPLICABLE_DISPLAY
    assert item.dataset is not None
    assert item.dataset.provider == "kaggle"
    assert item.dataset.version == "1.2.0"


def test_platform_display_uses_the_platform_value_for_real_platforms() -> None:
    assert make_item_summary(platform=PublicPlatform.youtube).platform_display == "youtube"


def test_item_detail_requires_a_sampling_disclosure() -> None:
    """The model disclosure is optional only because an item may be unclassified;
    the sampling disclosure is not, because it qualifies the item either way."""
    with pytest.raises(ValidationError) as exc_info:
        ItemDetail(**summary_fields(), score=0.42)

    missing = {error["loc"][0] for error in exc_info.value.errors()}
    assert "sampling_disclosure" in missing


def test_an_unclassified_item_reports_no_labels_rather_than_defaults() -> None:
    """A collected-but-not-yet-analysed item is a real state. Defaulting it to
    `uncertain` would put a label in the model's mouth that it never produced."""
    unclassified = make_item_summary(
        relevance=None,
        stance=None,
        severity=None,
        confidence_tier=None,
        review_state=ReviewState.model_only,
    )

    assert unclassified.is_classified is False
    assert unclassified.relevance is None
    assert unclassified.stance is None
    assert unclassified.severity is None
    assert unclassified.requires_review is False


def test_a_classified_item_reports_that_it_is_classified() -> None:
    assert make_item_summary().is_classified is True


def test_item_detail_score_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ItemDetail(
            **summary_fields(),
            score=1.5,
            model_name="gemini",
            model_version="v1",
            prompt_version="p1",
            taxonomy_version="t1",
            inferred_at=OBSERVED_AT,
            rationale=None,
            sampling_disclosure="Monitored sample only.",
        )


def test_responses_reject_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        make_item_summary(author_name="someone")


def test_item_summary_is_immutable() -> None:
    item = make_item_summary()

    with pytest.raises(ValidationError):
        item.severity = Severity.high


def test_hate_types_accept_the_controlled_taxonomy() -> None:
    item = make_item_summary(
        stance=Stance.likely_anti_muslim,
        hate_types=[HateType.collective_blame, HateType.exclusion],
        severity=Severity.moderate,
    )

    assert item.hate_types == [HateType.collective_blame, HateType.exclusion]


def test_dashboard_counts_must_nest() -> None:
    with pytest.raises(ValidationError):
        DashboardMetrics(
            observed_count=10,
            muslim_related_count=11,
            likely_anti_muslim_count=1,
            reviewed_count=0,
            likely_anti_muslim_rate=make_rate(),
        )

    with pytest.raises(ValidationError):
        DashboardMetrics(
            observed_count=10,
            muslim_related_count=4,
            likely_anti_muslim_count=5,
            reviewed_count=0,
            likely_anti_muslim_rate=make_rate(),
        )


def test_dashboard_response_carries_coverage_and_a_sampling_disclosure() -> None:
    response = DashboardResponse(
        coverage=CoverageSummary(
            last_success_at=None,
            coverage_score=None,
            data_mode=DataMode.fixture,
            is_stale=True,
            warnings=["No successful collection run yet."],
        ),
        metrics=DashboardMetrics(
            observed_count=10,
            muslim_related_count=10,
            likely_anti_muslim_count=2,
            reviewed_count=1,
            likely_anti_muslim_rate=make_rate(),
        ),
        trend=DashboardTrend(
            interval=MetricInterval.daily,
            points=[
                TrendPoint(
                    bucket_start=WINDOW_START,
                    is_gap=False,
                    observed_count=4,
                    muslim_related_count=4,
                    likely_anti_muslim_count=1,
                ),
                TrendPoint(bucket_start=OBSERVED_AT, is_gap=True),
            ],
        ),
        headlines=[
            HeadlineCard(
                item_id=uuid4(),
                headline="Synthetic headline",
                source_name="Synthetic wire",
                published_at=OBSERVED_AT,
                country_code="GB",
                geographic_scope="national",
                summary="Synthetic summary.",
                topic_labels=["policy_debate"],
            )
        ],
        sampling_disclosure="Rates describe the monitored sample, not the public.",
        meta=ResponseMeta(request_id="req_1", generated_at=OBSERVED_AT, data_mode=DataMode.fixture),
    )

    assert response.coverage.is_stale is True
    assert response.metrics.likely_anti_muslim_rate.denominator == 10
    assert response.sampling_disclosure
    # The uncollected day stays a gap with no counts, never a zero.
    gap = response.trend.points[1]
    assert gap.is_gap is True
    assert gap.observed_count is None


def test_a_trend_gap_must_not_carry_counts() -> None:
    with pytest.raises(ValidationError):
        TrendPoint(bucket_start=WINDOW_START, is_gap=True, observed_count=0)


def test_a_trend_bucket_that_is_not_a_gap_must_carry_counts() -> None:
    with pytest.raises(ValidationError):
        TrendPoint(bucket_start=WINDOW_START, is_gap=False)


def test_resource_entry_requires_review_provenance() -> None:
    entry = ResourceEntry(
        id=uuid4(),
        title="Reporting online hate",
        organization="Example Council",
        url="https://example.test/guide",
        country_scope="CA",
        category=ResourceCategory.responding_to_online_hate,
        summary="How to report anti-Muslim content on major platforms.",
        last_reviewed_at=OBSERVED_AT,
    )

    assert entry.category is ResourceCategory.responding_to_online_hate
    assert entry.last_reviewed_at == OBSERVED_AT

    with pytest.raises(ValidationError):
        ResourceEntry(
            id=uuid4(),
            title="Reporting online hate",
            organization="Example Council",
            url="https://example.test/guide",
            country_scope="CA",
            category=ResourceCategory.responding_to_online_hate,
            summary="How to report anti-Muslim content on major platforms.",
        )  # type: ignore[call-arg]
