"""Server-side verification of Supabase access tokens.

The browser's claim of identity is never trusted. Every token is verified here:
signature, issuer, audience, and expiry are all checked, and the subject must be
a UUID.

The product role is read from `app_metadata.role`, which only Supabase's
service-role key can set. The top-level `role` claim is Supabase's Postgres role
(`authenticated`) and is deliberately ignored — treating it as a product role
would grant every signed-in user the same privileges.

Supabase signs access tokens either with the project's shared HS256 secret or,
on projects using JWT signing keys, with an asymmetric ECC/RSA key whose public
half is published as a JWKS. Both are accepted: the token header selects which
key material is used, and an unrecognised algorithm falls through to the HS256
branch, where a signature check it cannot pass rejects it.
"""

import logging
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from amanah.auth.principal import AuthenticatedUser
from amanah.domain.enums import Role
from amanah.settings import SUPABASE_ACCESS_TOKEN_AUDIENCE, Settings

logger = logging.getLogger(__name__)

SUPABASE_TOKEN_ALGORITHM = "HS256"  # noqa: S105 - an algorithm name, not a credential

#: Algorithms Supabase uses for JWT signing keys. Verified against the project's
#: published public key, never against the shared secret.
SUPABASE_ASYMMETRIC_ALGORITHMS = ("ES256", "RS256")

#: How long a fetched JWKS stays usable before it is re-read. Long enough that
#: verification is not a per-request network call, short enough that a rotated
#: signing key is picked up without a restart.
_JWKS_CACHE_SECONDS = 600

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


@lru_cache(maxsize=4)
def _jwks_client(url: str, timeout_seconds: float) -> PyJWKClient:
    """One key client per JWKS URL, so the key set is fetched and cached once."""
    return PyJWKClient(
        url,
        cache_jwk_set=True,
        lifespan=_JWKS_CACHE_SECONDS,
        timeout=timeout_seconds,
    )


def _signing_key(token: str, settings: Settings) -> tuple[Any, str]:
    """Resolve the key and algorithm to verify `token` with.

    The algorithm named in the header only chooses between key sources; it can
    never weaken verification. An asymmetric header sends us to the published
    public key, and everything else -- including `none` -- is verified as HS256
    against the shared secret, which an attacker does not hold.
    """
    try:
        algorithm = str(jwt.get_unverified_header(token).get("alg", ""))
    except jwt.InvalidTokenError as exc:
        raise TokenVerificationError("malformed_header") from exc

    if algorithm not in SUPABASE_ASYMMETRIC_ALGORITHMS:
        return settings.supabase_jwt_secret.get_secret_value(), SUPABASE_TOKEN_ALGORITHM

    try:
        client = _jwks_client(settings.supabase_jwks_url, settings.http_read_timeout_seconds)
        return client.get_signing_key_from_jwt(token).key, algorithm
    except (PyJWKClientError, jwt.InvalidTokenError) as exc:
        # The project's public key could not be read or does not cover this
        # token. That is not the caller's fault, but it is still not a verified
        # token, so it is refused like any other.
        logger.warning("could not resolve a Supabase signing key", exc_info=exc)
        raise TokenVerificationError("signing_key_unavailable") from exc


def verify_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Verify a bearer token and return the caller it identifies.

    Raises `TokenVerificationError` for every rejection cause.
    """
    key, algorithm = _signing_key(token, settings)
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
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
