"""`/v1/dashboard` — coverage, deterministic metrics, trend, and headlines."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from amanah.api.ai import GeminiDependency
from amanah.api.dependencies import DatabaseSession, build_response_meta, get_settings
from amanah.api.schemas.dashboard import DashboardInsight, DashboardResponse
from amanah.api.schemas.filters import ItemFilters
from amanah.api.v1.mappers import SAMPLING_DISCLOSURE
from amanah.db.repositories.catalogue import SourceStatusRepository
from amanah.db.repositories.dashboard import DashboardRepository
from amanah.metrics.dashboard import DashboardData, build_dashboard
from amanah.metrics.facts import build_fact_bundle
from amanah.ml.insights import InsightService
from amanah.settings import Settings

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", summary="Read coverage, metrics, trend, and headlines")
def read_dashboard(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    filters: Annotated[ItemFilters, Query()],
    client: GeminiDependency,
) -> DashboardResponse:
    """Return the dashboard for the validated filters.

    Coverage precedes metrics in the payload as well as on the page: freshness
    and collection gaps are meant to be read before any aggregate number.

    The narrative summary is assembled last and is allowed to be absent. Every
    figure above it was counted in SQL, so an unavailable, over-budget, or
    unvalidated narrative costs the page its prose and nothing else
    (`spec.md` FR-INSIGHT-007).
    """
    data = build_dashboard(
        metrics_repository=DashboardRepository(session),
        sources_repository=SourceStatusRepository(session),
        filters=filters,
        data_mode=settings.data_mode,
    )
    insight, reason = _read_insight(session, filters, settings, client, data)

    return DashboardResponse(
        coverage=data.coverage,
        metrics=data.metrics,
        trend=data.trend,
        headlines=list(data.headlines),
        insight=insight,
        insight_unavailable_reason=reason,
        sampling_disclosure=SAMPLING_DISCLOSURE,
        meta=build_response_meta(settings, is_stale=data.is_stale, warnings=list(data.warnings)),
    )


def _read_insight(
    session: DatabaseSession,
    filters: ItemFilters,
    settings: Settings,
    client: GeminiDependency,
    dashboard: DashboardData,
) -> tuple[DashboardInsight | None, str | None]:
    """The cached narrative for these filters, or a stable reason it is absent.

    Built from the figures already computed above rather than recomputed, so the
    narrative describes exactly the numbers printed beside it.

    A cached snapshot is served without a model call, so returning to a dashboard
    whose data has not changed costs nothing (`spec.md` section 11.2). New data
    changes the bundle hash and therefore misses the cache, which is what makes
    each ETL run yield a current summary rather than a stale one.
    """
    if not client.is_configured:
        # Skip the bundle and the cache lookup entirely. With no key the answer
        # is already known, and this is the default state for the fixture and
        # demo deployments — the ones that serve this endpoint most.
        return None, "gemini_not_configured"

    bundle = build_fact_bundle(
        session, filters=filters, data_mode=settings.data_mode, dashboard=dashboard
    )
    result = InsightService(session, client=client).summarize(bundle)
    if result.output is None:
        return None, result.reason

    return (
        DashboardInsight(
            answer=result.output.answer,
            observations=list(result.output.observations),
            interpretation=list(result.output.interpretation),
            possible_association=list(result.output.possible_association),
            unknowns=list(result.output.unknowns),
            citations=[citation.fact_id for citation in result.output.citations],
        ),
        None,
    )
