"""Authenticated dashboard contract: headlines, coverage, and monitored-sample metrics."""

from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from amanah.api.schemas.base import ResponseModel, UtcDatetime
from amanah.api.schemas.common import CoverageSummary, MetricRate, ResponseMeta
from amanah.api.schemas.filters import CountryCode, NarrativeTag


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


class DashboardResponse(ResponseModel):
    """`GET /v1/dashboard` payload.

    Coverage precedes metrics so freshness and collection gaps are read before
    any aggregate number.
    """

    coverage: CoverageSummary
    metrics: DashboardMetrics
    headlines: list[HeadlineCard] = Field(default_factory=list)
    sampling_disclosure: str
    meta: ResponseMeta
