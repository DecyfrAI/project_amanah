"""Authenticated dashboard contract: headlines, coverage, and monitored-sample metrics."""

from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from amanah.api.schemas.base import ResponseModel, UtcDatetime
from amanah.api.schemas.common import CoverageSummary, MetricRate, ResponseMeta
from amanah.api.schemas.filters import CountryCode, NarrativeTag
from amanah.domain.enums import MetricInterval


class HeadlineCard(ResponseModel):
    """Current major headline relevant to Islamophobia or anti-Muslim hate."""

    item_id: UUID
    headline: str
    source_name: str
    published_at: UtcDatetime
    country_code: CountryCode | None
    geographic_scope: str | None
    summary: str
    topic_labels: list[NarrativeTag] = Field(default_factory=list)


class DashboardMetrics(ResponseModel):
    """Deterministic counts for the selected filters and window.

    `likely_anti_muslim_rate` is the likely anti-Muslim rhetoric rate *in the
    monitored sample*. It is not a measure of public sentiment, and the counts it
    is derived from are returned alongside it.
    """

    observed_count: int = Field(ge=0)
    muslim_related_count: int = Field(ge=0)
    likely_anti_muslim_count: int = Field(ge=0)
    reviewed_count: int = Field(ge=0)
    likely_anti_muslim_rate: MetricRate
    rate_change: float | None = Field(
        default=None,
        description="Change against the preceding window, or null when history is insufficient.",
    )

    @model_validator(mode="after")
    def _check_count_nesting(self) -> Self:
        if self.muslim_related_count > self.observed_count:
            raise ValueError("muslim_related_count must not exceed observed_count")
        if self.likely_anti_muslim_count > self.muslim_related_count:
            raise ValueError("likely_anti_muslim_count must not exceed muslim_related_count")
        if self.reviewed_count > self.observed_count:
            raise ValueError("reviewed_count must not exceed observed_count")
        return self


class TrendPoint(ResponseModel):
    """One position in the trend series.

    A bucket that was never computed is returned with `is_gap` set and every
    count `null`. It is never returned as zero: "we did not collect" and "we
    collected and found none" are different claims.
    """

    bucket_start: UtcDatetime
    is_gap: bool
    observed_count: int | None = Field(default=None, ge=0)
    muslim_related_count: int | None = Field(default=None, ge=0)
    likely_anti_muslim_count: int | None = Field(default=None, ge=0)
    coverage_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_gap_carries_no_counts(self) -> Self:
        if self.is_gap and self.observed_count is not None:
            raise ValueError("a gap must not carry counts")
        if not self.is_gap and self.observed_count is None:
            raise ValueError("a non-gap bucket must carry counts")
        return self


class DashboardTrend(ResponseModel):
    """The trend series and the bucket width it was computed at."""

    interval: MetricInterval
    points: list[TrendPoint] = Field(default_factory=list)


class DashboardResponse(ResponseModel):
    """`GET /v1/dashboard` payload.

    Coverage precedes metrics so freshness and collection gaps are read before
    any aggregate number.
    """

    coverage: CoverageSummary
    metrics: DashboardMetrics
    trend: DashboardTrend
    headlines: list[HeadlineCard] = Field(default_factory=list)
    sampling_disclosure: str
    meta: ResponseMeta
