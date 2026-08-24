"""Reusable authentication and authorization dependencies.

`require_authenticated_user` is applied to the `/v1` router itself, so a new
product endpoint is authenticated by default and cannot become anonymous by
someone forgetting to add a dependency.
"""

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from amanah.api.errors import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    ServiceUnavailableError,
)
from amanah.api.schemas.common import ResponseMeta
from amanah.auth.principal import AuthenticatedUser, satisfies_role
from amanah.auth.tokens import TokenVerificationError, verify_access_token
from amanah.db.session import Database, DatabaseUnavailableError
from amanah.domain.enums import Role
from amanah.observability.request_context import current_request_id, new_request_id
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: `auto_error=False` so a missing header reaches our handler and produces the
#: same envelope as an invalid one, rather than Starlette's default 403 body.
bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token.")


def get_settings(request: Request) -> Settings:
    """Return the settings validated when the application started."""
    settings: Settings = request.app.state.settings
    return settings


def require_authenticated_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Verify the bearer token and return the caller."""
    if credentials is None:
        logger.info(
            "authentication failed",
            extra={"reason": "missing_credentials", "path": request.url.path},
        )
        raise AuthenticationRequiredError

    try:
        user = verify_access_token(credentials.credentials, settings)
    except TokenVerificationError as exc:
        logger.info(
            "authentication failed",
            extra={"reason": exc.reason, "path": request.url.path},
        )
        raise AuthenticationRequiredError from exc

    logger.info(
        "authentication succeeded",
        extra={"user_id": str(user.user_id), "role": user.role.value, "path": request.url.path},
    )
    return user


CurrentUser = Annotated[AuthenticatedUser, Depends(require_authenticated_user)]


def _require_role(
    user: AuthenticatedUser, required: Role, path: str, settings: Settings
) -> AuthenticatedUser:
    if not settings.auth_enforce_role_gates:
        logger.warning(
            "role gate bypassed",
            extra={
                "user_id": str(user.user_id),
                "role": user.role.value,
                "required_role": required.value,
                "path": path,
                "reason": "auth_enforce_role_gates is off",
            },
        )
        return user
    if not satisfies_role(user.role, required):
        logger.warning(
            "authorization denied",
            extra={
                "user_id": str(user.user_id),
                "role": user.role.value,
                "required_role": required.value,
                "path": path,
            },
        )
        raise PermissionDeniedError
    return user


def require_reviewer(
    request: Request,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Allow reviewers and administrators only, unless role gates are off."""
    return _require_role(user, Role.reviewer, request.url.path, settings)


def require_administrator(
    request: Request,
    user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Allow administrators only, unless role gates are off."""
    return _require_role(user, Role.administrator, request.url.path, settings)


def ensure_resource_owner(user: AuthenticatedUser, owner_id: UUID) -> None:
    """Deny access to a resource the caller does not own.

    Reviewers and administrators reach other users' records through their own
    queues, never through an owner-scoped read, so no role bypasses this check.
    """
    if user.user_id != owner_id:
        logger.warning(
            "ownership check denied",
            extra={"user_id": str(user.user_id), "role": user.role.value},
        )
        raise PermissionDeniedError


def get_database(request: Request) -> Database:
    """Return the connection pool, or refuse the request.

    A service with no `DATABASE_URL` still starts and still answers `/healthz`
    and `/readyz`; it simply cannot answer a product read, and says so with a
    retryable `503` instead of a confusing empty result.
    """
    database: Database | None = request.app.state.database
    if database is None:
        logger.warning("product read refused", extra={"reason": "database_not_configured"})
        raise ServiceUnavailableError
    return database


def get_session(
    user: CurrentUser,
    database: Annotated[Database, Depends(get_database)],
) -> Iterator[Session]:
    """Yield a transaction scoped to the verified caller.

    Depending on `CurrentUser` is what makes the scoping unavoidable: a route
    cannot obtain a session without the server having decided who is calling, so
    the owner and role predicates in the projections always have an identity to
    evaluate.
    """
    try:
        with database.session_for(user) as session:
            yield session
    except DatabaseUnavailableError as exc:
        # Converted once, here at the boundary. The driver message stays in the
        # logs because it can name internal hosts.
        raise ServiceUnavailableError from exc


DatabaseSession = Annotated[Session, Depends(get_session)]


def build_response_meta(
    settings: Settings,
    *,
    is_stale: bool = False,
    warnings: list[str] | None = None,
) -> ResponseMeta:
    """Build the metadata envelope attached to product responses."""
    return ResponseMeta(
        request_id=current_request_id() or new_request_id(),
        generated_at=datetime.now(UTC),
        data_mode=settings.data_mode,
        is_stale=is_stale,
        warnings=warnings or [],
    )
