"""Import and startup smoke test (B-S1.5)."""

import pytest
from fastapi import FastAPI

from amanah.main import API_VERSION, create_app
from amanah.settings import ConfigurationError
from tests.conftest import TEST_ORIGIN, make_settings


def test_factory_builds_an_application_with_its_routes_mounted() -> None:
    app = create_app(make_settings())

    assert isinstance(app, FastAPI)
    assert app.version == API_VERSION
    assert set(app.openapi()["paths"]) == {
        "/healthz",
        "/readyz",
        "/v1/me",
        "/v1/dashboard",
        "/v1/items",
        "/v1/items/{item_id}",
        "/v1/news",
        "/v1/filters",
        "/v1/resources",
        "/v1/methodology",
        "/v1/connections",
        "/v1/assistant/query",
        "/v1/image-examples",
        "/v1/image-classifications",
        "/v1/admin/runs",
        "/v1/admin/runs/{run_id}",
    }


def test_factory_stores_the_validated_settings_for_dependencies() -> None:
    settings = make_settings()

    app = create_app(settings)

    assert app.state.settings is settings


def test_factory_fails_fast_when_core_configuration_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ORIGIN", raising=False)

    with pytest.raises(ConfigurationError):
        create_app()


def test_cors_is_restricted_to_the_configured_origins() -> None:
    app = create_app(make_settings())

    cors = next(
        middleware for middleware in app.user_middleware if "allow_origins" in middleware.kwargs
    )

    assert cors.kwargs["allow_origins"] == [TEST_ORIGIN]
    assert cors.kwargs["allow_credentials"] is True


def test_interactive_documentation_is_not_mounted() -> None:
    app = create_app(make_settings())

    assert app.docs_url is None
    assert app.redoc_url is None
