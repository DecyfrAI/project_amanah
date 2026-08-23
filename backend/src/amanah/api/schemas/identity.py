"""Contract for the authenticated caller's own record."""

from uuid import UUID

from amanah.api.schemas.base import ResponseModel
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import Role


class AuthenticatedIdentity(ResponseModel):
    """Who the server decided the caller is.

    Deliberately narrow: it carries the verified identifier and effective role
    and no contact details. Profile fields — display name, onboarding state, and
    content-safety preferences — are added when `user_profile` exists (B-S3).
    """

    user_id: UUID
    role: Role


class CurrentUserResponse(ResponseModel):
    """`GET /v1/me` payload."""

    profile: AuthenticatedIdentity
    meta: ResponseMeta
