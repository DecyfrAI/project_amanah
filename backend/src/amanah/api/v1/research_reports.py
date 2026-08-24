"""Creation, preview, and aggregate export for immutable research reports."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from amanah.api.dependencies import CurrentUser, DatabaseSession, build_response_meta, get_settings
from amanah.api.errors import ConflictError, ResourceNotFoundError
from amanah.api.schemas.research_reports import (
    CreateResearchReportRequest,
    ResearchReportResponse,
)
from amanah.db.repositories.catalogue import SourceStatusRepository
from amanah.db.repositories.dashboard import DashboardRepository
from amanah.db.repositories.research_reports import ResearchReportRepository
from amanah.observability.request_context import current_request_id, new_request_id
from amanah.reporting.research_reports import (
    ResearchReportExportUnavailableError,
    ResearchReportMissingError,
    ResearchReportService,
    to_research_report_snapshot,
)
from amanah.resources.methodology import build_methodology
from amanah.settings import Settings

router = APIRouter(prefix="/research-reports", tags=["research reports"])


def _service(session: DatabaseSession, settings: Settings) -> ResearchReportService:
    return ResearchReportService(
        reports=ResearchReportRepository(session),
        dashboard=DashboardRepository(session),
        sources=SourceStatusRepository(session),
        data_mode=settings.data_mode,
    )


def _request_id() -> str:
    return current_request_id() or new_request_id()


@router.post("", summary="Create an immutable research-report snapshot", status_code=201)
def create_research_report(
    request: CreateResearchReportRequest,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    user: CurrentUser,
) -> ResearchReportResponse:
    meta = build_response_meta(settings)
    row = _service(session, settings).create(
        request=request,
        user_id=user.user_id,
        methodology=build_methodology(settings, meta),
        request_id=meta.request_id,
    )
    return ResearchReportResponse(report=to_research_report_snapshot(row), meta=meta)


@router.get("/{report_id}", summary="Read an authorized research-report snapshot")
def read_research_report(
    report_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ResearchReportResponse:
    try:
        row = _service(session, settings).require_report(report_id)
    except ResearchReportMissingError as exc:
        raise ResourceNotFoundError("This research report was not found.") from exc
    return ResearchReportResponse(
        report=to_research_report_snapshot(row), meta=build_response_meta(settings)
    )


@router.get(
    "/{report_id}/summary.csv",
    summary="Download aggregate CSV from the stored report snapshot",
    response_class=Response,
)
def download_research_report_csv(
    report_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    user: CurrentUser,
) -> Response:
    try:
        content = _service(session, settings).aggregate_csv(
            report_id=report_id,
            actor_user_id=user.user_id,
            request_id=_request_id(),
        )
    except ResearchReportMissingError as exc:
        raise ResourceNotFoundError("This research report was not found.") from exc
    except ResearchReportExportUnavailableError as exc:
        raise ConflictError(str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="research-report-{report_id}.csv"'},
    )
