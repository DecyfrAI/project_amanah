"""Contracts for immutable, aggregate-only research-report snapshots."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import CoverageSummary, ResponseMeta
from amanah.api.schemas.filters import ItemFilters
from amanah.domain.enums import DataMode, RedactionMode, ResearchReportStatus


class ReportMetricKey(StrEnum):
    observed_count = "observed_count"
    muslim_related_count = "muslim_related_count"
    likely_anti_muslim_count = "likely_anti_muslim_count"
    reviewed_count = "reviewed_count"
    likely_anti_muslim_rate = "likely_anti_muslim_rate"


class ReportFindingKey(StrEnum):
    monitored_sample_rate = "monitored_sample_rate"
    analysis_coverage = "analysis_coverage"


class CreateResearchReportRequest(RequestModel):
    title: str = Field(min_length=3, max_length=200)
    filters: ItemFilters = Field(default_factory=ItemFilters)
    metrics: list[ReportMetricKey] = Field(
        default_factory=lambda: list(ReportMetricKey), min_length=1, max_length=5
    )
    findings: list[ReportFindingKey] = Field(
        default_factory=lambda: list(ReportFindingKey), max_length=2
    )
    include_aggregate_csv: bool = False
    redaction_mode: RedactionMode = RedactionMode.default_redacted

    @field_validator("metrics", "findings")
    @classmethod
    def _reject_duplicates(cls, values: list[StrEnum]) -> list[StrEnum]:
        if len(values) != len(set(values)):
            raise ValueError("selection values must be unique")
        return values


class ReportMetricSnapshot(ResponseModel):
    key: ReportMetricKey
    value: int | float | None
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, ge=0)


class ReportFindingSnapshot(ResponseModel):
    key: ReportFindingKey
    statement: str = Field(min_length=1, max_length=1_000)
    citation_ids: list[str] = Field(min_length=1)


class ReportCitation(ResponseModel):
    id: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern=r"^(aggregate|methodology)$")
    label: str = Field(min_length=1, max_length=500)


class ResearchReportSnapshot(ResponseModel):
    id: UUID
    user_id: UUID
    title: str
    filter_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    filters: ItemFilters
    data_version: str
    coverage: CoverageSummary
    metrics: list[ReportMetricSnapshot]
    findings: list[ReportFindingSnapshot]
    citations: list[ReportCitation]
    methodology_version: str
    methodology_disclosure: dict[str, object]
    limitations: list[str]
    source_scope: list[str]
    window_start: UtcDatetime
    window_end: UtcDatetime
    data_mode: DataMode
    redaction_mode: RedactionMode
    status: ResearchReportStatus
    aggregate_csv_available: bool
    created_at: UtcDatetime
    completed_at: UtcDatetime


class ResearchReportResponse(ResponseModel):
    report: ResearchReportSnapshot
    meta: ResponseMeta
