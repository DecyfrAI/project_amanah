"""Unauthenticated operational endpoints (B-S4.2)."""

from fastapi.testclient import TestClient

from amanah.main import create_app
from tests.conftest import TEST_DATABASE_URL, TEST_JWT_SECRET, make_settings


def test_liveness_is_reachable_without_a_session(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_degrades_when_the_configured_database_is_unreachable(
    client: TestClient,
) -> None:
    """Readiness makes a real round trip, so a configured-but-unreachable
    database is caught here rather than by the first product request. The test
    settings name a database that does not exist."""
    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"configuration": "ok", "database": "unavailable"},
    }


def test_readiness_degrades_when_the_database_is_not_configured() -> None:
    app = create_app(make_settings(database_url=None))

    with TestClient(app) as degraded_client:
        response = degraded_client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["database"] == "unavailable"


def test_optional_connectors_are_not_readiness_dependencies() -> None:
    """A missing connector key disables that connector and nothing else, so no
    connector may appear as a readiness check."""
    app = create_app(make_settings(gemini_api_key=None, youtube_api_key=None))

    with TestClient(app) as connectorless_client:
        response = connectorless_client.get("/readyz")

    checks = response.json()["checks"]
    assert set(checks) == {"configuration", "database"}
    assert checks["configuration"] == "ok"


def test_health_responses_disclose_no_secrets_or_internal_versions(client: TestClient) -> None:
    bodies = [client.get("/healthz").text, client.get("/readyz").text]

    for body in bodies:
        assert TEST_JWT_SECRET not in body
        assert TEST_DATABASE_URL not in body
        assert "version" not in body.lower()
        assert "supabase" not in body.lower()


def test_health_responses_carry_the_baseline_security_headers(client: TestClient) -> None:
    headers = client.get("/healthz").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "max-age=31536000" in headers["Strict-Transport-Security"]
