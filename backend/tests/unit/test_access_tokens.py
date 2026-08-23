"""Server-side access-token verification (B-S4.4)."""

from datetime import timedelta
from uuid import uuid4

import pytest

from amanah.auth.tokens import TokenVerificationError, verify_access_token
from amanah.domain.enums import Role
from amanah.settings import Settings
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
