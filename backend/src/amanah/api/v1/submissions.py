"""`/v1/submissions` and the unified contribution history (B-S16).

Authentication comes from the `/v1` router. Ownership is enforced twice below
that: the projections these reads use carry `user_id = amanah_current_user_id()`
in their own `WHERE` clause, and a record that is not the caller's therefore
answers `404` rather than `403` — telling a caller that a record they cannot read
exists is itself a disclosure.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from amanah.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    build_response_meta,
    get_settings,
)
from amanah.api.errors import ApiError, ResourceNotFoundError
from amanah.api.schemas.common import CursorPage, PageInfo
from amanah.api.schemas.contributions import (
    ContributionEventList,
    ContributionHistoryQuery,
    ContributionSummary,
    SubmissionResponse,
    SubmitUrlRequest,
)
from amanah.api.schemas.errors import ErrorCode
from amanah.api.v1.mappers import to_contribution, to_contribution_event, to_submission
from amanah.contributions.submissions import SubmissionRejectedError, SubmissionService
from amanah.db.pagination import InvalidCursorError
from amanah.db.repositories.contributions import ContributionRepository
from amanah.settings import Settings

router = APIRouter(tags=["contributions"])


def _invalid_cursor() -> ApiError:
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=400,
        message="The pagination cursor is not valid for this request.",
        details={"fields": ["cursor"]},
    )


@router.post(
    "/submissions",
    summary="Submit one public URL for analysis",
    status_code=status.HTTP_201_CREATED,
)
def submit_url(
    request: SubmitUrlRequest,
    response: Response,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SubmissionResponse:
    """Record the submission and queue the pipeline.

    Returns immediately with `processing` (`spec.md` FR-SUBMIT-005); retrieval
    happens in the background through the same canonical pipeline collected
    content uses. Resubmitting the same address answers `200` with the existing
    record rather than `201` with a second one.
    """
    service = SubmissionService(session)
    try:
        result = service.submit(user_id=user.user_id, submitted_url=request.url)
    except SubmissionRejectedError as exc:
        raise ApiError(
            code=ErrorCode.validation_failed,
            status_code=422,
            message="This address is not a public web page we can retrieve.",
            details={"fields": ["url"], "safe_error_code": exc.safe_error_code},
        ) from exc

    if not result.is_new:
        response.status_code = status.HTTP_200_OK

    stored = ContributionRepository(session).get_submission(result.submission.id)
    if stored is None:  # pragma: no cover - the row was written in this request
        raise ResourceNotFoundError("This submission was not found.")
    return SubmissionResponse(submission=to_submission(stored), meta=build_response_meta(settings))


@router.get("/submissions/{submission_id}", summary="Read one of your own submissions")
def read_submission(
    submission_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SubmissionResponse:
    """Return the caller's submission, or `404` if it is not theirs."""
    row = ContributionRepository(session).get_submission(submission_id)
    if row is None:
        raise ResourceNotFoundError("This submission was not found.")
    return SubmissionResponse(submission=to_submission(row), meta=build_response_meta(settings))


@router.get("/me/contributions", summary="List your own contributions")
def list_contributions(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[ContributionHistoryQuery, Query()],
) -> CursorPage[ContributionSummary]:
    """Return one page of the caller's history across every contribution type."""
    try:
        page = ContributionRepository(session).list_history(
            limit=query.limit,
            cursor=query.cursor,
            contribution_type=query.contribution_type,
        )
    except InvalidCursorError as exc:
        raise _invalid_cursor() from exc

    return CursorPage[ContributionSummary](
        items=[to_contribution(row) for row in page.rows],
        page=PageInfo(next_cursor=page.next_cursor, limit=query.limit),
        meta=build_response_meta(settings),
    )


@router.get(
    "/me/contributions/{contribution_id}/events",
    summary="Read the timeline of one of your contributions",
)
def list_contribution_events(
    contribution_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ContributionEventList:
    """Return every appended line on one contribution, oldest first.

    An unknown or someone else's identifier yields an empty list rather than a
    `404`: the projection simply has no rows for it, and distinguishing the two
    would confirm that a record exists.
    """
    events = ContributionRepository(session).list_events(contribution_id=contribution_id)
    return ContributionEventList(
        events=[to_contribution_event(row) for row in events],
        meta=build_response_meta(settings),
    )
