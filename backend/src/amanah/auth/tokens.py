"""Server-side verification of Supabase access tokens.

The browser's claim of identity is never trusted. Every token is verified here:
signature, issuer, audience, and expiry are all checked, and the subject must be
a UUID.

The product role is read from `app_metadata.role`, which only Supabase's
service-role key can set. The top-level `role` claim is Supabase's Postgres role
(`authenticated`) and is deliberately ignored — treating it as a product role
would grant every signed-in user the same privileges.
"""

import logging
from typing import Any
from uuid import UUID

import jwt

from amanah.auth.principal import AuthenticatedUser
from amanah.domain.enums import Role
from amanah.settings import SUPABASE_ACCESS_TOKEN_AUDIENCE, Settings

logger = logging.getLogger(__name__)

SUPABASE_TOKEN_ALGORITHM = "HS256"  # noqa: S105 - an algorithm name, not a credential

_REQUIRED_CLAIMS = ["exp", "iat", "sub", "aud", "iss"]


class TokenVerificationError(Exception):
    """A presented token is not usable.

    `reason` is a short code for logs only. Callers must not surface it: the API
    returns one indistinguishable `401` for every cause.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _read_role(claims: dict[str, Any]) -> Role:
    """Resolve the product role, defaulting to the least-privileged role."""
    app_metadata = claims.get("app_metadata")
    raw_role = app_metadata.get("role") if isinstance(app_metadata, dict) else None
    if raw_role is None:
        return Role.registered_user
    try:
        return Role(raw_role)
    except ValueError:
        logger.warning(
            "unrecognized role claim; defaulting to least privilege",
            extra={"user_id": str(claims.get("sub"))},
        )
        return Role.registered_user


def verify_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Verify a bearer token and return the caller it identifies.

    Raises `TokenVerificationError` for every rejection cause.
    """
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            settings.supabase_jwt_secret.get_secret_value(),
            algorithms=[SUPABASE_TOKEN_ALGORITHM],
            audience=SUPABASE_ACCESS_TOKEN_AUDIENCE,
            issuer=settings.supabase_token_issuer,
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenVerificationError("expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenVerificationError("invalid") from exc

    try:
        user_id = UUID(str(claims["sub"]))
    except ValueError as exc:
        raise TokenVerificationError("invalid_subject") from exc

    return AuthenticatedUser(user_id=user_id, role=_read_role(claims))
