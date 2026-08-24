"""The outer IP limit returns the standard envelope and Retry-After."""

from fastapi.testclient import TestClient

from amanah.main import create_app
from tests.conftest import make_settings


def test_product_requests_are_limited_but_health_checks_are_not() -> None:
    app = create_app(make_settings(api_rate_limit_requests=2, api_rate_limit_window_seconds=60))
    with TestClient(app) as client:
        assert client.get("/v1/me").status_code == 401
        assert client.get("/v1/me").status_code == 401
        limited = client.get("/v1/me")
        assert client.get("/healthz").status_code == 200

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) > 0
    assert limited.headers["X-RateLimit-Remaining"] == "0"
