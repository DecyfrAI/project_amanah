"""Default-deny behaviour of the `/v1` product router (B-S4.4, B-S4.7)."""

import re
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from amanah.api.errors import AUTHENTICATION_REQUIRED_MESSAGE
from amanah.domain.enums import Role
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
