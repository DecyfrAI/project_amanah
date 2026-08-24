"""`/v1/insights`, `/v1/captures`, `/v1/posts/*`, `/v1/me/posts` (B-S27, ADR 0004).

Reading a thread needs only a verified session; adding to one needs an
invitation. That asymmetry is ADR 0004's, and it is the difference between a
closed conversation and a private one: colleagues can follow the reasoning before
they are in a position to add to it.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Row

from amanah.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    build_response_meta,
    get_settings,
)
from amanah.api.errors import ApiError, ConflictError, PermissionDeniedError, ResourceNotFoundError
from amanah.api.schemas.common import CursorPage, PageInfo
from amanah.api.schemas.discussion import (
    CaptureResponse,
    CaptureSummary,
    CreateCaptureRequest,
    CreateInsightRequest,
    CreatePostRequest,
    DiscussionResponse,
    InsightListQuery,
    InsightResponse,
    InsightSummary,
    PostReactionCounts,
    PostResponse,
    ReactRequest,
    ViewerPostEntry,
    ViewerPostQuery,
)
from amanah.api.schemas.errors import ErrorCode
from amanah.api.v1.mappers import (
    to_capture,
    to_discussion_post,
    to_insight,
    to_reaction_counts,
    to_viewer_post,
)
from amanah.db.pagination import InvalidCursorError
from amanah.db.repositories.discussion import DiscussionRepository
from amanah.discussion.service import (
    CaptureRequest,
    DiscussionRejectedError,
    DiscussionService,
    ParticipationRequiredError,
    SnapshotRequest,
)
from amanah.settings import Settings

router = APIRouter(tags=["insights"])

#: Shown when an uninvited caller tries to write. `spec.md` and ADR 0004 make
#: participation an invitation rather than a setting, so the message says so
#: instead of implying the caller can enable it themselves.
NOT_INVITED_MESSAGE = "Discussion is invite-only. Ask a reviewer for an invitation."


def _invalid_cursor() -> ApiError:
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=400,
        message="The pagination cursor is not valid for this request.",
        details={"fields": ["cursor"]},
    )


def _rejection(exc: DiscussionRejectedError) -> ApiError:
    if exc.is_conflict:
        return ConflictError(exc.message)
    return ResourceNotFoundError(exc.message)


# -- insights -------------------------------------------------------------


@router.get("/insights", summary="List snapshot insights")
def list_insights(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[InsightListQuery, Query()],
) -> CursorPage[InsightSummary]:
    """Return one page of frozen figures, newest first."""
    try:
        page = DiscussionRepository(session).list_insights(limit=query.limit, cursor=query.cursor)
    except InvalidCursorError as exc:
        raise _invalid_cursor() from exc

    return CursorPage[InsightSummary](
        items=[to_insight(row) for row in page.rows],
        page=PageInfo(next_cursor=page.next_cursor, limit=query.limit),
        meta=build_response_meta(settings),
    )


@router.post(
    "/insights", summary="Freeze one figure as an insight", status_code=status.HTTP_201_CREATED
)
def create_insight(
    request: CreateInsightRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> InsightResponse:
    """Store the claim with the counts that produced it.

    The snapshot is immutable once written: the point of freezing a figure is
    that a later reader can check the claim against the same numbers, which a row
    that could be edited afterwards would not support.
    """
    insight = DiscussionService(session).create_snapshot(
        user_id=user.user_id,
        request=SnapshotRequest(
            title=request.title,
            claim=request.claim,
            metric=request.metric,
            numerator=request.numerator,
            denominator=request.denominator,
            window_start=request.window_start,
            window_end=request.window_end,
            figure_label=request.figure_label,
            filter_hash=request.filter_hash,
            explorer_href=request.explorer_href,
            source_keys=tuple(request.source_keys),
            items_observed=request.items_observed,
            items_relevant=request.items_relevant,
        ),
    )
    stored = DiscussionRepository(session).get_insight(insight.id)
    if stored is None:  # pragma: no cover - the row was written in this request
        raise ResourceNotFoundError("This insight was not found.")
    return InsightResponse(insight=to_insight(stored), meta=build_response_meta(settings))


@router.get("/insights/{insight_id}", summary="Read one snapshot insight")
def read_insight(
    insight_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> InsightResponse:
    row = DiscussionRepository(session).get_insight(insight_id)
    if row is None:
        raise ResourceNotFoundError("This insight was not found.")
    return InsightResponse(insight=to_insight(row), meta=build_response_meta(settings))


# -- discussion -----------------------------------------------------------


@router.get("/insights/{insight_id}/discussion", summary="Read the thread on one insight")
def read_discussion(
    insight_id: UUID,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DiscussionResponse:
    """Return every note on the insight, oldest first, retracted ones included.

    A retracted note keeps its place with a fixed notice in place of its body.
    Filtering it out would make the thread read as though the turn never
    happened.
    """
    repository = DiscussionRepository(session)
    if repository.get_insight(insight_id) is None:
        raise ResourceNotFoundError("This insight was not found.")

    rows = repository.list_thread(insight_id)
    return DiscussionResponse(
        insight_id=insight_id,
        posts=[
            to_discussion_post(row, capture=capture, reactions=reactions)
            for row, capture, reactions in _decorate(repository, rows)
        ],
        can_participate=DiscussionService(session).may_participate(user.user_id),
        meta=build_response_meta(settings),
    )


@router.post(
    "/insights/{insight_id}/discussion/posts",
    summary="Add a note to one insight",
    status_code=status.HTTP_201_CREATED,
)
def add_post(
    insight_id: UUID,
    request: CreatePostRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PostResponse:
    """Add one note. Requires an invitation (ADR 0004)."""
    try:
        post = DiscussionService(session).add_post(
            user_id=user.user_id,
            snapshot_insight_id=insight_id,
            body=request.body,
            dashboard_capture_id=request.capture_id,
        )
    except ParticipationRequiredError as exc:
        raise PermissionDeniedError(NOT_INVITED_MESSAGE) from exc
    except DiscussionRejectedError as exc:
        raise _rejection(exc) from exc

    return _post_response(session, post.id, settings)


@router.post("/posts/{post_id}/reactions", summary="React to one note")
def react_to_post(
    post_id: UUID,
    request: ReactRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PostResponse:
    """Record the caller's single reaction to one note.

    Reacting again replaces their own reaction rather than adding a second, so
    the endpoint is idempotent and the counts stay a count of people. Nothing
    aggregates these by author.
    """
    service = DiscussionService(session)
    try:
        service.react(post_id, user_id=user.user_id, kind=request.kind)
    except ParticipationRequiredError as exc:
        raise PermissionDeniedError(NOT_INVITED_MESSAGE) from exc
    except DiscussionRejectedError as exc:
        raise _rejection(exc) from exc

    return _post_response(session, post_id, settings)


@router.post("/posts/{post_id}/retract", summary="Retract your own note")
def retract_post(
    post_id: UUID,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PostResponse:
    """Withdraw one's own note, leaving the row in place (ADR 0004).

    The body is replaced with a fixed notice and the capture is removed. Doing it
    twice is idempotent and does not restamp the moment of withdrawal.
    """
    try:
        DiscussionService(session).retract(post_id, user_id=user.user_id)
    except DiscussionRejectedError as exc:
        raise _rejection(exc) from exc
    return _post_response(session, post_id, settings)


# -- captures and the caller's own notes ----------------------------------


@router.post(
    "/captures",
    summary="Store a first-party capture of an Amanah figure",
    status_code=status.HTTP_201_CREATED,
)
def create_capture(
    request: CreateCaptureRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CaptureResponse:
    """Store a capture of a figure this product rendered.

    Both paths are required to be relative and the database enforces it: an
    absolute URL would point the reader at somebody else's server, which is the
    screenshot board ADR 0004 refused.
    """
    try:
        capture = DiscussionService(session).create_capture(
            user_id=user.user_id,
            request=CaptureRequest(
                alt_text=request.alt_text,
                image_source=request.image_source,
                filter_hash=request.filter_hash,
                explorer_href=request.explorer_href,
            ),
        )
    except ParticipationRequiredError as exc:
        raise PermissionDeniedError(NOT_INVITED_MESSAGE) from exc

    stored = DiscussionRepository(session).get_capture(capture.id)
    if stored is None:  # pragma: no cover - the row was written in this request
        raise ResourceNotFoundError("This capture was not found.")
    return CaptureResponse(capture=to_capture(stored), meta=build_response_meta(settings))


@router.get("/me/posts", summary="List your own discussion notes")
def list_viewer_posts(
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[ViewerPostQuery, Query()],
) -> CursorPage[ViewerPostEntry]:
    """Return the caller's own notes so they can return to a thread they joined."""
    repository = DiscussionRepository(session)
    try:
        page = repository.list_posts_by_author(user.user_id, limit=query.limit, cursor=query.cursor)
    except InvalidCursorError as exc:
        raise _invalid_cursor() from exc

    return CursorPage[ViewerPostEntry](
        items=[
            to_viewer_post(row, capture=capture, reactions=reactions)
            for row, capture, reactions in _decorate(repository, page.rows)
        ],
        page=PageInfo(next_cursor=page.next_cursor, limit=query.limit),
        meta=build_response_meta(settings),
    )


type DecoratedPost = tuple[Row[Any], CaptureSummary | None, PostReactionCounts]


def _decorate(repository: DiscussionRepository, rows: tuple[Row[Any], ...]) -> list[DecoratedPost]:
    """Attach each note's capture and reaction counts in two queries, not 2N."""
    reactions = repository.reaction_counts(tuple(row.id for row in rows))
    captures = repository.captures(
        tuple(row.dashboard_capture_id for row in rows if row.dashboard_capture_id)
    )
    decorated: list[DecoratedPost] = []
    for row in rows:
        capture_row = captures.get(row.dashboard_capture_id)
        decorated.append(
            (
                row,
                to_capture(capture_row) if capture_row is not None else None,
                to_reaction_counts(reactions.get(row.id)),
            )
        )
    return decorated


def _post_response(session: DatabaseSession, post_id: UUID, settings: Settings) -> PostResponse:
    """Re-read one note through the projection so the response is what is stored."""
    repository = DiscussionRepository(session)
    row = repository.get_post(post_id)
    if row is None:
        raise ResourceNotFoundError("This note was not found.")
    stored, capture, reactions = _decorate(repository, (row,))[0]
    return PostResponse(
        post=to_discussion_post(stored, capture=capture, reactions=reactions),
        meta=build_response_meta(settings),
    )
