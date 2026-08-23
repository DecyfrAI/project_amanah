"""`/v1/admin/runs` — dispatch and read bounded collection runs (B-S7.6).

Every operation here requires the administrator role on top of the `/v1` router's
authentication. That is enforced twice on purpose: the route dependency refuses
the request, and the projections it reads carry an administrator predicate of
their own, so a routing mistake still cannot publish operational state.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from amanah.api.dependencies import (
    DatabaseSession,
    build_response_meta,
    get_settings,
    require_administrator,
)
from amanah.api.errors import ApiError, ResourceNotFoundError
from amanah.api.schemas.common import CursorPage, CursorPageRequest, PageInfo
from amanah.api.schemas.errors import ErrorCode
from amanah.api.schemas.runs import (
    CollectionRunResponse,
    CollectionRunSummary,
    CreateRunRequest,
)
from amanah.api.v1.mappers import to_background_job, to_collection_run
from amanah.auth.principal import AuthenticatedUser
from amanah.db.pagination import InvalidCursorError
from amanah.db.repositories.runs import CollectionRunRepository
from amanah.domain.enums import JobState
from amanah.jobs.runs import CollectionRunService, RunDispatch, RunValidationError
from amanah.settings import Settings

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_administrator)],
)

#: Adapter version recorded for a run dispatched by hand. The worker that picks
#: the run up replaces it with the version it actually executed, so a dispatch
#: never claims a capability the code does not have.
DISPATCH_ADAPTER_VERSION = "pending"


class AdminRunQuery(CursorPageRequest):
    """Validated filters for the run list."""

    source_key: str | None = None
    status: JobState | None = None


def _invalid_cursor() -> ApiError:
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=400,
        message="The pagination cursor is not valid for this request.",
        details={"fields": ["cursor"]},
    )


def _validation_error(exc: RunValidationError) -> ApiError:
    """Turn a bounds failure into a client error naming the field to fix."""
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=422,
        message=str(exc),
        details={"fields": [exc.field]},
    )


@router.get("/runs", summary="List collection runs")
def list_runs(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[AdminRunQuery, Query()],
) -> CursorPage[CollectionRunSummary]:
    """Return one page of runs, newest dispatch first."""
    try:
        page = CollectionRunRepository(session).list_runs(
            limit=query.limit,
            cursor=query.cursor,
            source_key=query.source_key,
            status=query.status,
        )
    except InvalidCursorError as exc:
        raise _invalid_cursor() from exc

    return CursorPage[CollectionRunSummary](
        items=[to_collection_run(row) for row in page.rows],
        page=PageInfo(next_cursor=page.next_cursor, limit=query.limit),
        meta=build_response_meta(settings),
    )


@router.get("/runs/{run_id}", summary="Read one collection run and its stages")
def read_run(
    run_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CollectionRunResponse:
    """Return the run with every stage it has produced so far."""
    repository = CollectionRunRepository(session)
    row = repository.get_run(run_id)
    if row is None:
        raise ResourceNotFoundError("This run was not found.")
    return CollectionRunResponse(
        run=to_collection_run(row),
        jobs=[to_background_job(job) for job in repository.list_jobs(run_id)],
        meta=build_response_meta(settings),
    )


@router.post(
    "/runs",
    summary="Dispatch one bounded collection run",
    status_code=status.HTTP_201_CREATED,
)
def create_run(
    request: CreateRunRequest,
    response: Response,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    administrator: Annotated[AuthenticatedUser, Depends(require_administrator)],
) -> CollectionRunResponse:
    """Create the run, or return the one this idempotency key already created.

    Redelivering the same request answers `200` with the existing run rather than
    `201` with a second one, so a retried dispatch cannot double-collect against
    a live provider.
    """
    dispatch = RunDispatch(
        source_key=request.source_key,
        mode=request.mode,
        adapter_version=DISPATCH_ADAPTER_VERSION,
        idempotency_key=request.idempotency_key,
        window_start=request.window_start,
        window_end=request.window_end,
        item_cap=request.item_cap,
        source_seed_entry_id=request.source_seed_entry_id,
        requested_by=administrator.user_id,
    )
    try:
        run, is_new = CollectionRunService(session).dispatch(dispatch)
    except RunValidationError as exc:
        raise _validation_error(exc) from exc

    if not is_new:
        response.status_code = status.HTTP_200_OK

    repository = CollectionRunRepository(session)
    stored = repository.get_run(run.id)
    if stored is None:  # pragma: no cover - the dependency already proved the role
        raise ResourceNotFoundError("This run was not found.")
    return CollectionRunResponse(
        run=to_collection_run(stored),
        jobs=[to_background_job(job) for job in repository.list_jobs(run.id)],
        meta=build_response_meta(settings),
    )
