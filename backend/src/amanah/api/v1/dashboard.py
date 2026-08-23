"""`/v1/dashboard` — coverage, deterministic metrics, trend, and headlines."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from amanah.api.dependencies import DatabaseSession, build_response_meta, get_settings
from amanah.api.schemas.dashboard import DashboardResponse
from amanah.api.schemas.filters import ItemFilters
from amanah.api.v1.mappers import SAMPLING_DISCLOSURE
from amanah.db.repositories.catalogue import SourceStatusRepository
from amanah.db.repositories.dashboard import DashboardRepository
from amanah.metrics.dashboard import build_dashboard
from amanah.settings import Settings

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", summary="Read coverage, metrics, trend, and headlines")
def read_dashboard(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    filters: Annotated[ItemFilters, Query()],
) -> DashboardResponse:
    """Return the dashboard for the validated filters.

    Coverage precedes metrics in the payload as well as on the page: freshness
    and collection gaps are meant to be read before any aggregate number.
    """
    data = build_dashboard(
        metrics_repository=DashboardRepository(session),
        sources_repository=SourceStatusRepository(session),
        filters=filters,
        data_mode=settings.data_mode,
    )
    return DashboardResponse(
        coverage=data.coverage,
        metrics=data.metrics,
        trend=data.trend,
        headlines=list(data.headlines),
        sampling_disclosure=SAMPLING_DISCLOSURE,
        meta=build_response_meta(settings, is_stale=data.is_stale, warnings=list(data.warnings)),
    )
