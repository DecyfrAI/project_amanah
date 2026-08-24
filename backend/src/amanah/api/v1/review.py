"""`/v1/review/*` — the reviewer queue and its append-only decisions (B-S17.4).

Every operation requires the reviewer role on top of the `/v1` router's
authentication, and that is enforced twice on purpose: the route dependency
refuses the request, and the projections carry a reviewer predicate of their own,
so a routing mistake still cannot publish the queue.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from amanah.api.dependencies import (
    DatabaseSession,
    build_response_meta,
    get_settings,
    require_reviewer,
)
from amanah.api.errors import ApiError, ConflictError, ResourceNotFoundError
from amanah.api.schemas.common import CursorPage, PageInfo
from amanah.api.schemas.errors import ErrorCode
from amanah.api.schemas.review import (
    AppendDecisionRequest,
    ReviewDecisionResponse,
    ReviewQueueQuery,
    ReviewTaskResponse,
    ReviewTaskSummary,
)
from amanah.api.v1.mappers import to_review_decision, to_review_task
from amanah.auth.principal import AuthenticatedUser
from amanah.contributions.review import (
    ClaimLostError,
    DecisionRequest,
    InvalidDecisionError,
    ReviewService,
)
from amanah.db.pagination import InvalidCursorError
from amanah.db.repositories.review import ReviewRepository
from amanah.settings import Settings

router = APIRouter(
    prefix="/review",
    tags=["review"],
    dependencies=[Depends(require_reviewer)],
)


def _task_response(
    session: DatabaseSession, task_id: UUID, settings: Settings
) -> ReviewTaskResponse:
    repository = ReviewRepository(session)
    row = repository.get_task(task_id)
    if row is None:
        raise ResourceNotFoundError("This review task was not found.")
    return ReviewTaskResponse(
        task=to_review_task(row),
        decisions=[to_review_decision(event) for event in repository.list_decisions(task_id)],
        meta=build_response_meta(settings),
    )


@router.get("/tasks", summary="List the review queue")
def list_tasks(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[ReviewQueueQuery, Query()],
) -> CursorPage[ReviewTaskSummary]:
    """Return one page of the queue, highest priority and oldest first."""
    try:
        page = ReviewRepository(session).list_tasks(
            limit=query.limit,
            cursor=query.cursor,
            status=query.status,
            task_type=query.task_type,
        )
    except InvalidCursorError as exc:
        raise ApiError(
            code=ErrorCode.validation_failed,
            status_code=400,
            message="The pagination cursor is not valid for this request.",
            details={"fields": ["cursor"]},
        ) from exc

    return CursorPage[ReviewTaskSummary](
        items=[to_review_task(row) for row in page.rows],
        page=PageInfo(next_cursor=page.next_cursor, limit=query.limit),
        meta=build_response_meta(settings),
    )


@router.get("/tasks/{task_id}", summary="Read one review task and its decisions")
def read_task(
    task_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReviewTaskResponse:
    """Return the task with every decision appended to it so far."""
    return _task_response(session, task_id, settings)


@router.post("/tasks/{task_id}/claim", summary="Claim one review task")
def claim_task(
    task_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
) -> ReviewTaskResponse:
    """Take the task under a lease, or refuse because another reviewer has it.

    Re-claiming a task the caller already holds renews their own lease rather
    than failing, so a reviewer whose page reloaded does not lose their place.
    """
    try:
        ReviewService(session).claim(task_id, reviewer_id=reviewer.user_id)
    except ClaimLostError as exc:
        raise ConflictError("Another reviewer is working on this task.") from exc
    return _task_response(session, task_id, settings)


@router.post(
    "/tasks/{task_id}/decisions",
    summary="Append one decision to a review task",
    status_code=status.HTTP_201_CREATED,
)
def append_decision(
    task_id: UUID,
    request: AppendDecisionRequest,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
) -> ReviewDecisionResponse:
    """Append the decision, update the effective labels, and resolve the disputes.

    The prediction is untouched. What changes is the item's effective review
    state, the task's status, and the disputing users' timelines.
    """
    service = ReviewService(session)
    try:
        event = service.decide(
            task_id,
            reviewer_id=reviewer.user_id,
            request=DecisionRequest(
                decision=request.decision,
                note=request.note,
                corrected_labels=request.corrected_labels,
                is_training_candidate=request.is_training_candidate,
            ),
        )
    except ClaimLostError as exc:
        raise ConflictError("Claim this task before deciding on it.") from exc
    except InvalidDecisionError as exc:
        raise ApiError(
            code=ErrorCode.validation_failed,
            status_code=422,
            message=exc.message,
        ) from exc

    decisions = ReviewRepository(session).list_decisions(task_id)
    appended = next(row for row in decisions if row.id == event.id)
    return ReviewDecisionResponse(
        decision=to_review_decision(appended), meta=build_response_meta(settings)
    )
