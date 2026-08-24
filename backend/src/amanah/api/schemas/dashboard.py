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


class DashboardInsight(ResponseModel):
    """A validated narrative summary of the figures above it.

    Every field is optional except the separation itself. `observations` restates
    what the stored facts say; `interpretation` is what a reader might take from
    that; `possible_association` is co-occurrence and never a cause; `unknowns`
    is what this data cannot answer. Keeping them apart is what stops a reader
    from absorbing an interpretation as an observation.

    `citations` names the figure behind every quantitative claim, each already
    verified against the fact bundle server-side. An insight that failed that
    verification is not returned at all.
    """

    answer: str
    observations: list[str] = Field(default_factory=list)
    interpretation: list[str] = Field(default_factory=list)
    possible_association: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    citations: list[str] = Field(
        default_factory=list, description="Fact ids supporting the quantitative claims."
    )


class DashboardResponse(ResponseModel):
    """`GET /v1/dashboard` payload.

    Coverage precedes metrics so freshness and collection gaps are read before
    any aggregate number.
    """

    coverage: CoverageSummary
    metrics: DashboardMetrics
    trend: DashboardTrend
    headlines: list[HeadlineCard] = Field(default_factory=list)
    #: Null whenever AI is unavailable, over budget, or its output failed
    #: citation validation. `spec.md` FR-INSIGHT-007: the deterministic figures
    #: above are unaffected and the page stays useful without this.
    insight: DashboardInsight | None = None
    insight_unavailable_reason: str | None = Field(
        default=None,
        description="Stable code explaining an absent narrative. Never a provider message.",
    )
    sampling_disclosure: str
    meta: ResponseMeta
