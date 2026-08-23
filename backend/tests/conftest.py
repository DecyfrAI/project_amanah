"""Shared fixtures and safe factories.

Every credential here is synthetic and local to the test process. No fixture
reads the ambient environment, so a developer's real configuration can never
leak into a test run.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from amanah.auth.tokens import SUPABASE_TOKEN_ALGORITHM
from amanah.domain.enums import Role
from amanah.main import create_app
from amanah.settings import SUPABASE_ACCESS_TOKEN_AUDIENCE, Settings

TEST_SUPABASE_URL = "https://project.supabase.co"
TEST_JWT_SECRET = "test-only-signing-secret-0123456789"
TEST_ORIGIN = "http://localhost:5173"
TEST_DATABASE_URL = "postgresql://amanah:local@localhost:5432/amanah_test"


def make_settings(**overrides: Any) -> Settings:
    """Build settings with safe defaults; tests override only what they assert on."""
    values: dict[str, Any] = {
        "app_origin": TEST_ORIGIN,
        "supabase_url": TEST_SUPABASE_URL,
        "supabase_jwt_secret": TEST_JWT_SECRET,
        "database_url": TEST_DATABASE_URL,
    }
    values.update(overrides)
    return Settings(**values)


def make_access_token(
    settings: Settings,
    *,
    user_id: UUID | str | None = None,
    role: Role | str | None = None,
    expires_in: timedelta = timedelta(hours=1),
    audience: str = SUPABASE_ACCESS_TOKEN_AUDIENCE,
    issuer: str | None = None,
    secret: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    omit_claims: tuple[str, ...] = (),
) -> str:
    """Mint a Supabase-shaped access token.

    Defaults produce a valid token; every argument exists so a test can make
    exactly one thing wrong.
    """
    issued_at = datetime.now(tz=UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id if user_id is not None else uuid4()),
        "aud": audience,
        "iss": issuer if issuer is not None else settings.supabase_token_issuer,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + expires_in).timestamp()),
        # Supabase always sets this to its Postgres role, never to a product role.
        "role": "authenticated",
    }
    if role is not None:
        claims["app_metadata"] = {"role": role.value if isinstance(role, Role) else role}
    if extra_claims:
        claims.update(extra_claims)
    for claim in omit_claims:
        claims.pop(claim, None)
    return jwt.encode(
        claims,
        secret if secret is not None else settings.supabase_jwt_secret.get_secret_value(),
        algorithm=SUPABASE_TOKEN_ALGORITHM,
    )


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authorization_header(settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(settings)}"}
