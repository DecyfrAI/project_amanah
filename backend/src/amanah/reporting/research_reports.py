"""Build immutable research reports from deterministic stored aggregates."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from amanah.api.schemas.dashboard import DashboardMetrics
from amanah.api.schemas.methodology import MethodologyResponse
from amanah.api.schemas.research_reports import (
    CreateResearchReportRequest,
    ReportCitation,
    ReportFindingKey,
    ReportFindingSnapshot,
    ReportMetricKey,
    ReportMetricSnapshot,
    ResearchReportSnapshot,
)
from amanah.db.models.resources import ResearchReport
from amanah.db.repositories.catalogue import SourceStatusRepository
from amanah.db.repositories.dashboard import DashboardRepository
from amanah.db.repositories.research_reports import ResearchReportRepository
from amanah.domain.enums import DataMode, ResearchReportStatus
from amanah.metrics.dashboard import build_dashboard

logger = logging.getLogger(__name__)


class ResearchReportError(ValueError):
    """A safe expected report-generation failure."""


class ResearchReportMissingError(ResearchReportError):
    """The report does not exist or is outside the caller's authorization."""


class ResearchReportExportUnavailableError(ResearchReportError):
    """The snapshot was not created with aggregate CSV in scope."""


class ResearchReportService:
    """Freeze report facts and render every export from the stored snapshot."""

    def __init__(
        self,
        *,
        reports: ResearchReportRepository,
        dashboard: DashboardRepository,
        sources: SourceStatusRepository,
        data_mode: DataMode,
    ) -> None:
        self._reports = reports
        self._dashboard = dashboard
        self._sources = sources
        self._data_mode = data_mode

    def create(
        self,
        *,
        request: CreateResearchReportRequest,
        user_id: UUID,
        methodology: MethodologyResponse,
        request_id: str,
    ) -> Row[Any]:
        moment = datetime.now(UTC)
        filters_payload = request.filters.model_dump(mode="json", exclude_none=True)
        filter_hash = _filter_hash(filters_payload)
        data_version = self._reports.resolve_data_version(request.filters)
        dashboard = build_dashboard(
            metrics_repository=self._dashboard,
            sources_repository=self._sources,
            filters=request.filters,
            data_mode=self._data_mode,
            now=moment,
        )
        rate = dashboard.metrics.likely_anti_muslim_rate
        aggregate_citation_id = f"aggregate:{filter_hash[:16]}:{data_version}"
        methodology_citation_id = f"methodology:{methodology.methodology_version}"
        citations = [
            ReportCitation(
                id=aggregate_citation_id,
                kind="aggregate",
                label="Frozen deterministic aggregates for this report's exact filters.",
            ),
            ReportCitation(
                id=methodology_citation_id,
                kind="methodology",
                label="Versioned Project Amanah methodology and limitations.",
            ),
        ]
        metrics = _selected_metrics(request.metrics, dashboard.metrics)
        findings = _selected_findings(
            request.findings,
            observed_count=dashboard.metrics.observed_count,
            analysed_count=(
                dashboard.metrics.observed_count
                - self._dashboard.count_unclassified(request.filters)
            ),
            rate_numerator=rate.numerator,
            rate_denominator=rate.denominator,
            aggregate_citation_id=aggregate_citation_id,
        )
        methodology_payload = methodology.model_dump(mode="json", exclude={"meta"})
        sections: dict[str, object] = {
            "title": request.title,
            "metrics": [metric.model_dump(mode="json") for metric in metrics],
            "findings": [finding.model_dump(mode="json") for finding in findings],
            "citations": [citation.model_dump(mode="json") for citation in citations],
            "methodology_disclosure": methodology_payload,
            "limitations": list(methodology.limitations),
            "source_scope": list(rate.source_scope),
            "window_start": rate.window_start.isoformat(),
            "window_end": rate.window_end.isoformat(),
            "data_mode": self._data_mode.value,
            "aggregate_csv_available": request.include_aggregate_csv,
        }
        report = ResearchReport(
            user_id=user_id,
            filter_hash=filter_hash,
            filters=filters_payload,
            data_version=data_version,
            coverage_snapshot=dashboard.coverage.model_dump(mode="json"),
            sections=sections,
            citation_ids=[citation.id for citation in citations],
            methodology_version=methodology.methodology_version,
            redaction_mode=request.redaction_mode,
            status=ResearchReportStatus.ready,
            completed_at=moment,
        )
        self._reports.create_report(report)
        self._reports.add_audit_event(
            report_id=report.id,
            actor_user_id=user_id,
            action="generated",
            request_id=request_id,
        )
        self._reports.commit()
        logger.info(
            "research report generated",
            extra={
                "report_id": str(report.id),
                "user_id": str(user_id),
                "filter_hash": filter_hash,
                "data_version": data_version,
            },
        )
        return self.require_report(report.id)

    def require_report(self, report_id: UUID) -> Row[Any]:
        row = self._reports.get_report(report_id)
        if row is None:
            raise ResearchReportMissingError("This research report was not found.")
        return row

    def aggregate_csv(self, *, report_id: UUID, actor_user_id: UUID, request_id: str) -> str:
        snapshot = to_research_report_snapshot(self.require_report(report_id))
        if not snapshot.aggregate_csv_available:
            raise ResearchReportExportUnavailableError(
                "Aggregate CSV was not included when this snapshot was generated."
            )
        content = _render_aggregate_csv(snapshot)
        self._reports.add_audit_event(
            report_id=report_id,
            actor_user_id=actor_user_id,
            action="downloaded",
            request_id=request_id,
        )
        self._reports.commit()
        logger.info(
            "research report aggregate downloaded",
            extra={"report_id": str(report_id), "user_id": str(actor_user_id)},
        )
        return content


def _filter_hash(filters: dict[str, object]) -> str:
    payload = json.dumps(filters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _selected_metrics(
    selected: list[ReportMetricKey], metrics: DashboardMetrics
) -> list[ReportMetricSnapshot]:
    rate = metrics.likely_anti_muslim_rate
    available = {
        ReportMetricKey.observed_count: ReportMetricSnapshot(
            key=ReportMetricKey.observed_count, value=metrics.observed_count
        ),
        ReportMetricKey.muslim_related_count: ReportMetricSnapshot(
            key=ReportMetricKey.muslim_related_count, value=metrics.muslim_related_count
        ),
        ReportMetricKey.likely_anti_muslim_count: ReportMetricSnapshot(
            key=ReportMetricKey.likely_anti_muslim_count,
            value=metrics.likely_anti_muslim_count,
        ),
        ReportMetricKey.reviewed_count: ReportMetricSnapshot(
            key=ReportMetricKey.reviewed_count, value=metrics.reviewed_count
        ),
        ReportMetricKey.likely_anti_muslim_rate: ReportMetricSnapshot(
            key=ReportMetricKey.likely_anti_muslim_rate,
            value=rate.value,
            numerator=rate.numerator,
            denominator=rate.denominator,
        ),
    }
    return [available[key] for key in selected]


def _selected_findings(
    selected: list[ReportFindingKey],
    *,
    observed_count: int,
    analysed_count: int,
    rate_numerator: int,
    rate_denominator: int,
    aggregate_citation_id: str,
) -> list[ReportFindingSnapshot]:
    if rate_denominator == 0:
        rate_statement = (
            "No monitored-sample rate is available because the selected window contains "
            "no Muslim-related denominator."
        )
    else:
        rate_statement = (
            f"The selected monitored sample contains {rate_numerator} likely anti-Muslim "
            f"items among {rate_denominator} Muslim-related items."
        )
    findings = {
        ReportFindingKey.monitored_sample_rate: ReportFindingSnapshot(
            key=ReportFindingKey.monitored_sample_rate,
            statement=rate_statement,
            citation_ids=[aggregate_citation_id],
        ),
        ReportFindingKey.analysis_coverage: ReportFindingSnapshot(
            key=ReportFindingKey.analysis_coverage,
            statement=(
                f"Analysis coverage is based on {analysed_count} analysed records among "
                f"{observed_count} observed records in the selected sample."
            ),
            citation_ids=[aggregate_citation_id],
        ),
    }
    return [findings[key] for key in selected]


def to_research_report_snapshot(row: Row[Any]) -> ResearchReportSnapshot:
    sections = dict(row.sections)
    return ResearchReportSnapshot(
        id=row.id,
        user_id=row.user_id,
        title=sections["title"],
        filter_hash=row.filter_hash,
        filters=row.filters,
        data_version=row.data_version,
        coverage=row.coverage_snapshot,
        metrics=sections["metrics"],
        findings=sections["findings"],
        citations=sections["citations"],
        methodology_version=row.methodology_version,
        methodology_disclosure=sections["methodology_disclosure"],
        limitations=sections["limitations"],
        source_scope=sections["source_scope"],
        window_start=sections["window_start"],
        window_end=sections["window_end"],
        data_mode=sections["data_mode"],
        redaction_mode=row.redaction_mode,
        status=row.status,
        aggregate_csv_available=sections["aggregate_csv_available"],
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _safe_csv_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _render_aggregate_csv(snapshot: ResearchReportSnapshot) -> str:
    output = io.StringIO(newline="")
    columns = (
        "metric_key",
        "value",
        "numerator",
        "denominator",
        "window_start",
        "window_end",
        "source_scope",
        "coverage_score",
        "data_version",
        "methodology_version",
        "data_mode",
        "redaction_mode",
    )
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for metric in snapshot.metrics:
        writer.writerow(
            {
                "metric_key": metric.key.value,
                "value": metric.value,
                "numerator": metric.numerator,
                "denominator": metric.denominator,
                "window_start": snapshot.window_start.isoformat(),
                "window_end": snapshot.window_end.isoformat(),
                "source_scope": _safe_csv_cell("|".join(snapshot.source_scope)),
                "coverage_score": snapshot.coverage.coverage_score,
                "data_version": snapshot.data_version,
                "methodology_version": snapshot.methodology_version,
                "data_mode": snapshot.data_mode.value,
                "redaction_mode": snapshot.redaction_mode.value,
            }
        )
    return output.getvalue()
