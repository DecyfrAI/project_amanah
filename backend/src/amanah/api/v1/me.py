"""`/v1/me` — the authenticated caller's own record and profile state."""

from typing import Annotated

from fastapi import APIRouter, Depends

from amanah.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    build_response_meta,
    get_settings,
)
from amanah.api.schemas.discussion import UpdateProfileRequest
from amanah.api.schemas.identity import AuthenticatedIdentity, CurrentUserResponse
from amanah.db.repositories.profile import ProfileRepository, ProfileService
from amanah.settings import Settings

router = APIRouter(tags=["profile"])


@router.get("/me", summary="Read the authenticated caller's own record")
def read_current_user(
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
    """Return the identity the server verified, plus any stored profile state.

    The role reported here is the server's decision from the verified token, not
    the stored row: a stale or tampered `user_profiles.role` must never be able
    to grant access on its own. Profile fields that have never been written come
    back as their defaults rather than as an error.
    """
    stored = ProfileRepository(session).get(user.user_id)
    return CurrentUserResponse(
        profile=AuthenticatedIdentity(
            user_id=user.user_id,
            role=user.role,
            display_name=stored.display_name if stored else None,
            onboarding_status=(
                stored.onboarding_status if stored else AuthenticatedIdentity.default_onboarding()
            ),
            content_safety_preferences=(dict(stored.content_safety_preferences) if stored else {}),
        ),
        meta=build_response_meta(settings),
    )


@router.patch("/me", summary="Update the caller's own profile and onboarding state")
def update_current_user(
    request: UpdateProfileRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUserResponse:
    """Persist profile and onboarding state for the caller (B-S27.1, spec 13.2).

    Only the caller's own row: the identifier comes from the verified token and
    is never accepted from the body. Role is likewise written from the token, so
    a client cannot name its own privileges.
    """
    ProfileService(session).update(
        user_id=user.user_id,
        role=user.role,
        display_name=request.display_name,
        onboarding_status=request.onboarding_status,
        content_safety_preferences=request.content_safety_preferences,
    )
    return read_current_user(user, session, settings)
