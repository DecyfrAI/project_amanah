"""Every failure leaves the service as the same safe envelope (B-S2.4, B-S2.6, B-S4.3).

A few routes exist only inside this module. They exercise paths no production
endpoint can reach yet — an unhandled exception, a reviewer-only route, an
owner-scoped route, a filtered collection — without adding unfinished endpoints
to the application. They are mounted on a router that reuses the real `/v1`
dependency list, so they are authenticated exactly like a product endpoint.
"""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import APIRouter, Depends, FastAPI, Query
from fastapi.testclient import TestClient

from amanah.api.dependencies import CurrentUser, ensure_resource_owner, require_reviewer
from amanah.api.schemas.filters import ItemFilters
from amanah.api.v1.router import v1_router
from amanah.auth.principal import AuthenticatedUser
from amanah.domain.enums import Role
from amanah.main import create_app
from amanah.settings import Settings
from tests.conftest import TEST_DATABASE_URL, TEST_JWT_SECRET, make_access_token, make_settings

SECRET_INTERNAL_DETAIL = "connection to 10.0.0.7:5432 refused"


def build_testing_router() -> APIRouter:
    """Routes that exist only for these tests, guarded like real `/v1` routes."""
    router = APIRouter(prefix="/v1/testing", dependencies=v1_router.dependencies)

    @router.get("/boom")
    def raise_unexpected() -> None:
        raise RuntimeError(SECRET_INTERNAL_DETAIL)

    @router.get("/reviewer-only")
    def reviewer_only(
        reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
    ) -> dict[str, str]:
        return {"role": reviewer.role.value}

    @router.get("/owned/{owner_id}")
    def owned(owner_id: UUID, user: CurrentUser) -> dict[str, str]:
        ensure_resource_owner(user, owner_id)
        return {"owner_id": str(owner_id)}

    @router.get("/filtered")
    def filtered(filters: Annotated[ItemFilters, Query()]) -> dict[str, int]:
        return {"country_count": len(filters.country_codes or [])}

    return router


@pytest.fixture
def failing_app() -> FastAPI:
    app = create_app(make_settings())
    app.include_router(build_testing_router())
    return app


@pytest.fixture
def failing_client(failing_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(failing_app, raise_server_exceptions=False) as test_client:
        yield test_client


def authorized(settings: Settings, role: Role | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(settings, role=role)}"}


def test_unknown_route_returns_the_error_envelope(client: TestClient) -> None:
    response = client.get("/v1/does-not-exist")

    assert response.status_code == 404
    assert set(response.json()["error"]) == {
        "code",
        "message",
        "request_id",
        "retryable",
        "details",
    }


def test_method_not_allowed_returns_the_error_envelope(client: TestClient) -> None:
    response = client.post("/healthz")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_unexpected_failure_never_leaks_internal_detail(
    failing_client: TestClient, settings: Settings
) -> None:
    response = failing_client.get("/v1/testing/boom", headers=authorized(settings))

    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "INTERNAL_ERROR"
    assert body["retryable"] is False
    assert SECRET_INTERNAL_DETAIL not in response.text
    assert "Traceback" not in response.text
    assert TEST_JWT_SECRET not in response.text
    assert TEST_DATABASE_URL not in response.text


def test_unauthenticated_caller_cannot_reach_a_failing_route(failing_client: TestClient) -> None:
    response = failing_client.get("/v1/testing/boom")

    assert response.status_code == 401


def test_base_role_is_denied_a_reviewer_route(
    failing_client: TestClient, settings: Settings
) -> None:
    response = failing_client.get(
        "/v1/testing/reviewer-only", headers=authorized(settings, Role.registered_user)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.parametrize("role", [Role.reviewer, Role.administrator])
def test_privileged_roles_reach_a_reviewer_route(
    failing_client: TestClient, settings: Settings, role: Role
) -> None:
    response = failing_client.get("/v1/testing/reviewer-only", headers=authorized(settings, role))

    assert response.status_code == 200


def test_owner_scoped_route_denies_another_user(
    failing_client: TestClient, settings: Settings
) -> None:
    response = failing_client.get(
        f"/v1/testing/owned/{uuid4()}", headers=authorized(settings, Role.administrator)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_supported_filters_are_accepted_over_http(
    failing_client: TestClient, settings: Settings
) -> None:
    response = failing_client.get(
        "/v1/testing/filtered",
        params={"country_codes": ["CA", "GB"]},
        headers=authorized(settings),
    )

    assert response.status_code == 200
    assert response.json() == {"country_count": 2}


def test_unsupported_filter_is_a_client_error_not_a_broader_query(
    failing_client: TestClient, settings: Settings
) -> None:
    response = failing_client.get(
        "/v1/testing/filtered",
        params={"author_name": "someone"},
        headers=authorized(settings),
    )

    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "UNSUPPORTED_FILTER"
    assert "author_name" in " ".join(body["details"]["fields"])


def test_invalid_filter_value_reports_the_field_but_never_the_value(
    failing_client: TestClient, settings: Settings
) -> None:
    response = failing_client.get(
        "/v1/testing/filtered",
        params={"country_codes": ["not-a-country-code"]},
        headers=authorized(settings),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "not-a-country-code" not in response.text


def test_unexpected_failure_stays_correlated_with_the_request(
    failing_client: TestClient, settings: Settings
) -> None:
    """The 500 path runs above the request-id middleware, so it is the one most
    likely to lose correlation."""
    response = failing_client.get(
        "/v1/testing/boom",
        headers={**authorized(settings), "X-Request-Id": "req_correlate-me"},
    )

    assert response.status_code == 500
    assert response.headers["X-Request-Id"] == "req_correlate-me"
    assert response.json()["error"]["request_id"] == "req_correlate-me"


def test_denial_response_carries_the_same_request_id_in_header_and_body(
    client: TestClient,
) -> None:
    response = client.get("/v1/me")

    assert response.headers["X-Request-Id"] == response.json()["error"]["request_id"]
