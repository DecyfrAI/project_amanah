"""Contract for the authenticated caller's own record."""

from typing import Any
from uuid import UUID

from pydantic import Field

from amanah.api.schemas.base import ResponseModel
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import OnboardingStatus, Role


class AuthenticatedIdentity(ResponseModel):
    """Who the server decided the caller is, plus their stored profile state.

    `role` is the effective role from the *verified token*, never the stored
    `user_profiles.role`. Keeping the two apart is what stops a stale or tampered
    row from granting anything; the profile fields beside it are ordinary state
    the caller owns and may change through `PATCH /v1/me`.
    """

    user_id: UUID
    role: Role
    display_name: str | None = None
    onboarding_status: OnboardingStatus = OnboardingStatus.not_started
    content_safety_preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="Reveal preferences for redacted text and blurred media.",
    )

    @staticmethod
    def default_onboarding() -> OnboardingStatus:
        """What a caller who has never written a profile row is reported as."""
        return OnboardingStatus.not_started


class CurrentUserResponse(ResponseModel):
    """`GET /v1/me` and `PATCH /v1/me` payload."""

    profile: AuthenticatedIdentity
    meta: ResponseMeta
