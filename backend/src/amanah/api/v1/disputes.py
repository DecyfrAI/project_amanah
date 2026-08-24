"""`/v1/items/{id}/disputes` and `/v1/disputes/{id}` (B-S17.1, B-S17.2).

Opening a dispute never changes the prediction. It creates a review task and
moves the item's effective review state, both of which are projections over
history rather than edits to it.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from amanah.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    build_response_meta,
    get_settings,
)
from amanah.api.errors import ApiError, ResourceNotFoundError
from amanah.api.schemas.contributions import (
    DisputeResponse,
    OpenDisputeRequest,
)
from amanah.api.schemas.errors import ErrorCode
from amanah.api.v1.mappers import to_dispute
from amanah.contributions.disputes import DisputeRejectedError, DisputeService
from amanah.db.repositories.contributions import ContributionRepository
from amanah.settings import Settings

router = APIRouter(tags=["contributions"])


@router.post(
    "/items/{content_item_id}/disputes",
    summary="Dispute the classification on one item",
    status_code=status.HTTP_201_CREATED,
)
def open_dispute(
    content_item_id: UUID,
    request: OpenDisputeRequest,
    response: Response,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DisputeResponse:
    """Open a dispute, or return the open one the caller already has.

    `spec.md` section 14.6 allows one open dispute per user and item, so a
    repeated request answers `200` with the existing record. A resolved dispute
    does not block a new one on fresh evidence.
    """
    try:
        result = DisputeService(session).open(
            user_id=user.user_id,
            content_item_id=content_item_id,
            reason=request.reason,
        )
    except DisputeRejectedError as exc:
        raise ApiError(
            code=ErrorCode.validation_failed,
            status_code=422,
            message=exc.message,
            details={"safe_error_code": exc.safe_error_code},
        ) from exc

    if not result.is_new:
        response.status_code = status.HTTP_200_OK

    stored = ContributionRepository(session).get_dispute(result.dispute.id)
    if stored is None:  # pragma: no cover - the row was written in this request
        raise ResourceNotFoundError("This dispute was not found.")
    return DisputeResponse(dispute=to_dispute(stored), meta=build_response_meta(settings))


@router.get("/disputes/{dispute_id}", summary="Read one of your own disputes")
def read_dispute(
    dispute_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DisputeResponse:
    """Return the caller's dispute, or `404` if it is not theirs."""
    row = ContributionRepository(session).get_dispute(dispute_id)
    if row is None:
        raise ResourceNotFoundError("This dispute was not found.")
    return DisputeResponse(dispute=to_dispute(row), meta=build_response_meta(settings))
