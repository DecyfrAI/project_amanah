"""Shared contract conventions: UTC timestamps, rates, and pagination (B-S2.3, B-S2.5, B-S2.6)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from amanah.api.schemas.common import (
    MAX_PAGE_LIMIT,
    CursorPageRequest,
    MetricRate,
    PageInfo,
    ResponseMeta,
)
from amanah.domain.enums import DataMode

WINDOW_START = datetime(2026, 1, 1, tzinfo=UTC)
WINDOW_END = datetime(2026, 1, 8, tzinfo=UTC)


def make_rate(*, numerator: int = 3, denominator: int = 12) -> MetricRate:
    return MetricRate(
        numerator=numerator,
        denominator=denominator,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        source_scope=["youtube_enriched_seed"],
        data_mode=DataMode.fixture,
    )


def test_rate_reports_its_numerator_denominator_and_scope() -> None:
    rate = make_rate(numerator=3, denominator=12)

    assert rate.value == pytest.approx(0.25)
    assert rate.numerator == 3
    assert rate.denominator == 12
    assert rate.source_scope == ["youtube_enriched_seed"]


def test_rate_with_no_observations_is_a_gap_not_zero() -> None:
    assert make_rate(numerator=0, denominator=0).value is None


def test_rate_requires_a_denominator() -> None:
    with pytest.raises(ValidationError):
        MetricRate(
            numerator=3,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
            source_scope=["news"],
            data_mode=DataMode.live,
        )  # type: ignore[call-arg]


def test_rate_numerator_cannot_exceed_its_denominator() -> None:
    with pytest.raises(ValidationError):
        make_rate(numerator=13, denominator=12)


def test_rate_window_must_not_run_backwards() -> None:
    with pytest.raises(ValidationError):
        MetricRate(
            numerator=1,
            denominator=2,
            window_start=WINDOW_END,
            window_end=WINDOW_START,
            source_scope=["news"],
            data_mode=DataMode.live,
        )


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ResponseMeta(
            request_id="req_1",
            generated_at=datetime(2026, 1, 1),  # a naive value is the point here
            data_mode=DataMode.live,
        )


def test_aware_timestamps_are_normalized_to_utc() -> None:
    meta = ResponseMeta(
        request_id="req_1",
        generated_at=datetime(2026, 1, 1, 5, tzinfo=timezone(timedelta(hours=5))),
        data_mode=DataMode.live,
    )

    assert meta.generated_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert meta.generated_at.tzinfo == UTC


def test_response_meta_serializes_snake_case_keys() -> None:
    meta = ResponseMeta(request_id="req_1", generated_at=WINDOW_START, data_mode=DataMode.fixture)

    assert set(meta.model_dump()) == {
        "request_id",
        "generated_at",
        "data_mode",
        "is_stale",
        "warnings",
    }


def test_last_page_reports_a_null_cursor() -> None:
    assert PageInfo(limit=25).next_cursor is None


def test_page_limit_is_bounded() -> None:
    assert CursorPageRequest().limit == 25

    with pytest.raises(ValidationError):
        CursorPageRequest(limit=MAX_PAGE_LIMIT + 1)
    with pytest.raises(ValidationError):
        CursorPageRequest(limit=0)


def test_oversized_cursor_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CursorPageRequest(cursor="x" * 513)
