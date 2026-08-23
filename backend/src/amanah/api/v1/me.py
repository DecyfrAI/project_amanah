"""`/v1/me` — the authenticated caller's own record."""

from typing import Annotated

from fastapi import APIRouter, Depends

from amanah.api.dependencies import CurrentUser, build_response_meta, get_settings
from amanah.api.schemas.identity import AuthenticatedIdentity, CurrentUserResponse
from amanah.settings import Settings

router = APIRouter(tags=["profile"])


@router.get("/me", summary="Read the authenticated caller's own record")
def read_current_user(
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
    """Return the identity and role the server verified for this request.

    The role reported here is the server's decision, not the client's claim; the
    frontend uses it for navigation only.
    """
    return CurrentUserResponse(
        profile=AuthenticatedIdentity(user_id=user.user_id, role=user.role),
        meta=build_response_meta(settings),
    )
