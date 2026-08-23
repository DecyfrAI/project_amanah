"""`/v1/filters`, `/v1/resources`, `/v1/methodology`, and `/v1/connections`.

Four small authenticated reads that describe the data rather than return it:
which filter values exist, which resources have been reviewed, how the numbers
were produced, and how collection is doing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from amanah.api.dependencies import DatabaseSession, build_response_meta, get_settings
from amanah.api.schemas.common import MAX_PAGE_LIMIT
from amanah.api.schemas.connections import ConnectionsResponse
from amanah.api.schemas.filters import (
    MAX_FILTER_WINDOW,
    DatasetOption,
    FilterOptionsResponse,
    ItemSort,
)
from amanah.api.schemas.methodology import MethodologyResponse
from amanah.api.schemas.resources import ResourceListResponse
from amanah.api.v1.mappers import to_connection_state, to_resource_entry
from amanah.db.repositories.catalogue import (
    FilterValueRepository,
    ResourceRepository,
    SourceStatusRepository,
)
from amanah.domain.enums import (
    ConfidenceTier,
    ContentKind,
    PublicPlatform,
    ResourceCategory,
    ReviewState,
    Severity,
)
from amanah.resources.methodology import build_methodology
from amanah.settings import Settings

router = APIRouter(tags=["catalogue"])


@router.get("/filters", summary="Read the filter values present in the data")
def read_filters(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FilterOptionsResponse:
    """Return the allowed filter values and the bounds a query must respect.

    Value lists come from stored rows, so the interface cannot offer a filter
    that returns an empty page for reasons the reader would misread as a finding.
    The closed vocabularies — severity, review state, confidence tier — are
    returned in full, because their meaning does not depend on what happens to
    have been collected.
    """
    repository = FilterValueRepository(session)
    return FilterOptionsResponse(
        content_kinds=[ContentKind(value) for value in repository.content_kinds()],
        platforms=[PublicPlatform(value) for value in repository.platforms()],
        datasets=[
            DatasetOption(
                provider=row.dataset_provider,
                name=row.dataset_name,
                version=row.dataset_version,
            )
            for row in repository.datasets()
        ],
        country_codes=list(repository.country_codes()),
        narrative_tags=list(repository.narrative_tags()),
        severities=list(Severity),
        review_states=list(ReviewState),
        confidence_tiers=list(ConfidenceTier),
        sorts=list(ItemSort),
        max_window_days=MAX_FILTER_WINDOW.days,
        max_page_limit=MAX_PAGE_LIMIT,
        meta=build_response_meta(settings),
    )


@router.get("/resources", summary="Read the reviewed education-resource catalogue")
def read_resources(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    category: ResourceCategory | None = None,
    country_scope: str | None = None,
) -> ResourceListResponse:
    """Return published resource entries only.

    Draft and archived entries are absent from the underlying projection, so an
    unreviewed description cannot reach a reader through this route.
    """
    rows = ResourceRepository(session).list_resources(
        category=category, country_scope=country_scope
    )
    return ResourceListResponse(
        resources=[to_resource_entry(row) for row in rows],
        categories=list(ResourceCategory),
        meta=build_response_meta(settings),
    )


@router.get("/methodology", summary="Read the methodology and its limitations")
def read_methodology(
    settings: Annotated[Settings, Depends(get_settings)],
) -> MethodologyResponse:
    """Return the versioned methodology disclosure.

    Deliberately not database-backed: this is reviewed prose that changes through
    a code review, and it needs no product data to answer, so it stays available
    even when collection is degraded.
    """
    return build_methodology(settings, build_response_meta(settings))


@router.get("/connections", summary="Read safe source coverage and connector state")
def read_connections(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectionsResponse:
    """Return each configured source's purpose, state, and freshness.

    The projection behind this has no column for a key, a connection string, a
    host, or a provider response body, so none of them can appear here.
    """
    repository = SourceStatusRepository(session)
    rows = repository.list_sources()
    return ConnectionsResponse(
        connections=[to_connection_state(row) for row in rows],
        data_mode=settings.data_mode,
        last_success_at=repository.latest_success_at(),
        meta=build_response_meta(settings),
    )
