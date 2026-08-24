"""Server-side access-token verification (B-S4.4)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.exceptions import PyJWKClientError

from amanah.auth import tokens
from amanah.auth.tokens import TokenVerificationError, verify_access_token
from amanah.domain.enums import Role
from amanah.settings import SUPABASE_ACCESS_TOKEN_AUDIENCE, Settings
from tests.conftest import make_access_token


def test_valid_token_identifies_the_caller(settings: Settings) -> None:
    user_id = uuid4()

    user = verify_access_token(make_access_token(settings, user_id=user_id), settings)

    assert user.user_id == user_id


def test_token_without_a_product_role_gets_the_least_privileged_role(settings: Settings) -> None:
    user = verify_access_token(make_access_token(settings), settings)

    assert user.role is Role.registered_user


@pytest.mark.parametrize("role", [Role.reviewer, Role.administrator])
def test_product_role_is_read_from_app_metadata(settings: Settings, role: Role) -> None:
    user = verify_access_token(make_access_token(settings, role=role), settings)

    assert user.role is role


def test_supabase_postgres_role_claim_does_not_grant_product_privileges(
    settings: Settings,
) -> None:
    token = make_access_token(settings, extra_claims={"role": "administrator"})

    assert verify_access_token(token, settings).role is Role.registered_user


def test_unrecognized_role_falls_back_to_least_privilege(settings: Settings) -> None:
    token = make_access_token(settings, role="superuser")

    assert verify_access_token(token, settings).role is Role.registered_user


def test_expired_token_is_rejected(settings: Settings) -> None:
    token = make_access_token(settings, expires_in=timedelta(minutes=-5))

    with pytest.raises(TokenVerificationError) as exc_info:
        verify_access_token(token, settings)

    assert exc_info.value.reason == "expired"


def test_token_signed_with_another_secret_is_rejected(settings: Settings) -> None:
    token = make_access_token(settings, secret="a-different-secret-0123456789abcd")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token, settings)


def test_token_from_another_issuer_is_rejected(settings: Settings) -> None:
    token = make_access_token(settings, issuer="https://attacker.example/auth/v1")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token, settings)


def test_token_for_another_audience_is_rejected(settings: Settings) -> None:
    token = make_access_token(settings, audience="anon")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token, settings)


@pytest.mark.parametrize("claim", ["exp", "iat", "sub", "aud", "iss"])
def test_token_missing_a_required_claim_is_rejected(settings: Settings, claim: str) -> None:
    token = make_access_token(settings, omit_claims=(claim,))

    with pytest.raises(TokenVerificationError):
        verify_access_token(token, settings)


def test_token_with_a_non_uuid_subject_is_rejected(settings: Settings) -> None:
    token = make_access_token(settings, user_id="not-a-uuid")

    with pytest.raises(TokenVerificationError) as exc_info:
        verify_access_token(token, settings)

    assert exc_info.value.reason == "invalid_subject"


def test_unsigned_token_is_rejected(settings: Settings) -> None:
    with pytest.raises(TokenVerificationError):
        verify_access_token("not.a.token", settings)


class _StubSigningKey:
    """Stands in for the `PyJWK` a real JWKS lookup would return."""

    def __init__(self, key: object) -> None:
        self.key = key


class _StubJwksClient:
    """Serves one public key without touching the network."""

    def __init__(self, key: object) -> None:
        self._key = key
        self.calls = 0

    def get_signing_key_from_jwt(self, token: str) -> _StubSigningKey:
        self.calls += 1
        return _StubSigningKey(self._key)


@pytest.fixture
def ec_key() -> ec.EllipticCurvePrivateKey:
    """A P-256 key pair standing in for the project's JWT signing key."""
    return ec.generate_private_key(ec.SECP256R1())


def _es256_token(
    settings: Settings,
    private_key: ec.EllipticCurvePrivateKey,
    *,
    user_id: UUID | None = None,
    role: Role | None = None,
) -> str:
    """Mint an ES256 access token the way a Supabase signing key would."""
    issued_at = datetime.now(tz=UTC)
    claims: dict[str, object] = {
        "sub": str(user_id if user_id is not None else uuid4()),
        "aud": SUPABASE_ACCESS_TOKEN_AUDIENCE,
        "iss": settings.supabase_token_issuer,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(hours=1)).timestamp()),
        "role": "authenticated",
    }
    if role is not None:
        claims["app_metadata"] = {"role": role.value}
    return jwt.encode(claims, private_key, algorithm="ES256")


def test_jwks_url_is_derived_from_the_project_url(settings: Settings) -> None:
    assert settings.supabase_jwks_url == f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"


def test_asymmetric_token_is_verified_against_the_published_key(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    ec_key: ec.EllipticCurvePrivateKey,
) -> None:
    user_id = uuid4()
    client = _StubJwksClient(ec_key.public_key())
    monkeypatch.setattr(tokens, "_jwks_client", lambda *_args: client)

    user = verify_access_token(_es256_token(settings, ec_key, user_id=user_id), settings)

    assert user.user_id == user_id
    assert client.calls == 1


def test_asymmetric_token_still_carries_the_product_role(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    ec_key: ec.EllipticCurvePrivateKey,
) -> None:
    monkeypatch.setattr(tokens, "_jwks_client", lambda *_args: _StubJwksClient(ec_key.public_key()))

    token = _es256_token(settings, ec_key, role=Role.reviewer)

    assert verify_access_token(token, settings).role is Role.reviewer


def test_asymmetric_token_signed_by_another_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    ec_key: ec.EllipticCurvePrivateKey,
) -> None:
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(tokens, "_jwks_client", lambda *_args: _StubJwksClient(ec_key.public_key()))

    with pytest.raises(TokenVerificationError):
        verify_access_token(_es256_token(settings, attacker_key), settings)


def test_unreadable_jwks_rejects_the_token(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    ec_key: ec.EllipticCurvePrivateKey,
) -> None:
    class _UnreachableJwksClient:
        def get_signing_key_from_jwt(self, token: str) -> object:
            raise PyJWKClientError("jwks unavailable")

    monkeypatch.setattr(tokens, "_jwks_client", lambda *_args: _UnreachableJwksClient())

    with pytest.raises(TokenVerificationError) as exc_info:
        verify_access_token(_es256_token(settings, ec_key), settings)

    assert exc_info.value.reason == "signing_key_unavailable"


def test_hs256_token_is_not_verified_against_the_published_key(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    ec_key: ec.EllipticCurvePrivateKey,
) -> None:
    """A shared-secret token must never reach the JWKS path."""
    client = _StubJwksClient(ec_key.public_key())
    monkeypatch.setattr(tokens, "_jwks_client", lambda *_args: client)

    verify_access_token(make_access_token(settings), settings)

    assert client.calls == 0
