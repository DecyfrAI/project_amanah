"""Default-deny behaviour of the `/v1` product router (B-S4.4, B-S4.6, B-S4.7)."""

import logging
import re
from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from amanah.api.dependencies import ensure_resource_owner
from amanah.api.errors import AUTHENTICATION_REQUIRED_MESSAGE, PermissionDeniedError
from amanah.auth.principal import AuthenticatedUser
from amanah.domain.enums import Role
from amanah.observability.logging import JsonLogFormatter
from amanah.settings import Settings
from tests.conftest import make_access_token

PRODUCT_ROUTE = "/v1/me"


def v1_operations(app: FastAPI) -> list[tuple[str, str]]:
    """Every published `/v1` operation as a (method, concrete path) pair."""
    operations: list[tuple[str, str]] = []
    for path, methods in app.openapi()["paths"].items():
        if not path.startswith("/v1"):
            continue
        concrete = re.sub(r"\{[^}]+\}", str(uuid4()), path)
        operations.extend((method.upper(), concrete) for method in methods)
    return operations


def test_every_published_v1_operation_denies_anonymous_callers(
    app: FastAPI, client: TestClient
) -> None:
    """Authentication is attached to the router, so this holds for endpoints
    added in later milestones without any change here."""
    operations = v1_operations(app)

    assert operations, "no /v1 operations are published"
    for method, path in operations:
        response = client.request(method, path)
        assert response.status_code == 401, f"{method} {path} was not denied"
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_anonymous_request_is_denied(client: TestClient) -> None:
    response = client.get(PRODUCT_ROUTE)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    body = response.json()["error"]
    assert body["code"] == "AUTHENTICATION_REQUIRED"
    assert body["retryable"] is False
    assert body["request_id"]


@pytest.mark.parametrize(
    "authorization",
    [
        "",
        "Bearer",
        "Bearer not.a.token",
        "Basic dXNlcjpwYXNz",
        "Token abc",
    ],
)
def test_malformed_credentials_are_denied(client: TestClient, authorization: str) -> None:
    response = client.get(PRODUCT_ROUTE, headers={"Authorization": authorization})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_expired_and_forged_tokens_are_indistinguishable_to_the_caller(
    client: TestClient, settings: Settings
) -> None:
    """A caller must not learn *why* a token was refused."""
    expired = make_access_token(settings, expires_in=timedelta(minutes=-1))
    forged = make_access_token(settings, secret="attacker-controlled-secret-01234567")
    missing = None

    responses = [
        client.get(PRODUCT_ROUTE, headers={"Authorization": f"Bearer {expired}"}),
        client.get(PRODUCT_ROUTE, headers={"Authorization": f"Bearer {forged}"}),
        client.get(PRODUCT_ROUTE),
    ]

    assert missing is None
    assert {response.status_code for response in responses} == {401}
    messages = {response.json()["error"]["message"] for response in responses}
    assert messages == {AUTHENTICATION_REQUIRED_MESSAGE}


def test_token_from_another_issuer_is_denied(client: TestClient, settings: Settings) -> None:
    token = make_access_token(settings, issuer="https://attacker.example/auth/v1")

    response = client.get(PRODUCT_ROUTE, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_valid_session_receives_the_verified_identity(
    client: TestClient, settings: Settings
) -> None:
    user_id = uuid4()
    token = make_access_token(settings, user_id=user_id, role=Role.reviewer)

    response = client.get(PRODUCT_ROUTE, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["profile"] == {"user_id": str(user_id), "role": "reviewer"}
    assert body["meta"]["request_id"] == response.headers["X-Request-Id"]


def test_response_echoes_a_generated_request_id(client: TestClient) -> None:
    request_id = client.get("/healthz").headers["X-Request-Id"]

    assert request_id.startswith("req_")


def test_forged_request_id_header_is_replaced(client: TestClient) -> None:
    forged = 'req_x"\n{"level":"error"}'

    response = client.get("/healthz", headers={"X-Request-Id": forged})

    assert response.headers["X-Request-Id"] != forged
    assert response.headers["X-Request-Id"].startswith("req_")


def test_safe_request_id_header_is_preserved_for_correlation(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-Id": "req_client-supplied-1"})

    assert response.headers["X-Request-Id"] == "req_client-supplied-1"


def test_request_ids_do_not_leak_between_requests(client: TestClient) -> None:
    """The middleware deliberately does not reset the context variable, so this
    guards against one request inheriting another's identifier."""
    first = client.get("/healthz", headers={"X-Request-Id": "req_first-caller"})
    second = client.get("/healthz")

    assert first.headers["X-Request-Id"] == "req_first-caller"
    assert second.headers["X-Request-Id"] != "req_first-caller"
    assert second.headers["X-Request-Id"].startswith("req_")


class RecordingHandler(logging.Handler):
    """Capture rendered log lines exactly as the service would emit them."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(JsonLogFormatter())
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


@pytest.fixture
def captured_logs() -> Iterator[RecordingHandler]:
    """Attach after the application factory has configured logging, since the
    factory replaces the root handlers."""
    handler = RecordingHandler()
    root = logging.getLogger()
    root.addHandler(handler)
    previous_level = root.level
    root.setLevel(logging.INFO)
    try:
        yield handler
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)


def test_successful_authentication_is_logged_without_the_token(
    client: TestClient, settings: Settings, captured_logs: RecordingHandler
) -> None:
    user_id = uuid4()
    token = make_access_token(settings, user_id=user_id, role=Role.reviewer)

    response = client.get(PRODUCT_ROUTE, headers={"Authorization": f"Bearer {token}"})
    logged = "\n".join(captured_logs.lines)

    assert response.status_code == 200
    # The outcome is recorded, so removing the log line fails this test.
    assert "authentication succeeded" in logged
    assert str(user_id) in logged
    assert "reviewer" in logged
    # ...but never the credential that produced it.
    assert token not in logged
    assert settings.supabase_jwt_secret.get_secret_value() not in logged


def test_failed_authentication_is_logged_without_the_rejected_token(
    client: TestClient, settings: Settings, captured_logs: RecordingHandler
) -> None:
    forged = make_access_token(settings, secret="attacker-controlled-secret-01234567")

    response = client.get(PRODUCT_ROUTE, headers={"Authorization": f"Bearer {forged}"})
    logged = "\n".join(captured_logs.lines)

    assert response.status_code == 401
    assert "authentication failed" in logged
    # The precise reason stays in the logs even though the caller never sees it.
    assert '"reason": "invalid"' in logged
    assert forged not in logged


def test_authorization_denial_is_logged_without_the_token(
    settings: Settings, captured_logs: RecordingHandler
) -> None:
    """Role denial happens on a route mounted only for the error-envelope tests,
    so it is exercised here through the same dependency."""
    user = AuthenticatedUser(user_id=uuid4(), role=Role.registered_user)

    with pytest.raises(PermissionDeniedError):
        ensure_resource_owner(user, uuid4())

    logged = "\n".join(captured_logs.lines)
    assert "ownership check denied" in logged
    assert str(user.user_id) in logged
    assert settings.supabase_jwt_secret.get_secret_value() not in logged
