"""Startup configuration validation (B-S4.1)."""

import pytest
from pydantic import ValidationError

from amanah.domain.enums import DataMode
from amanah.settings import (
    SECRET_PLACEHOLDER,
    ConfigurationError,
    Settings,
    load_settings,
)
from tests.conftest import TEST_JWT_SECRET, make_settings


def test_load_settings_names_missing_core_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("APP_ORIGIN", "SUPABASE_URL", "SUPABASE_JWT_SECRET"):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    message = str(exc_info.value)
    assert "APP_ORIGIN" in message
    assert "SUPABASE_URL" in message
    assert "SUPABASE_JWT_SECRET" in message


def test_load_settings_error_never_contains_a_secret_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("SUPABASE_URL", "not-a-url")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert TEST_JWT_SECRET not in str(exc_info.value)
    assert "not-a-url" not in str(exc_info.value)


def test_supabase_url_must_be_https() -> None:
    with pytest.raises(ValidationError):
        make_settings(supabase_url="http://project.supabase.co")


def test_token_issuer_is_derived_from_the_supabase_url() -> None:
    settings = make_settings(supabase_url="https://project.supabase.co/")
    assert settings.supabase_token_issuer == "https://project.supabase.co/auth/v1"


def test_allowed_origins_splits_a_comma_separated_list() -> None:
    settings = make_settings(app_origin="https://amanah.example, http://localhost:5173")
    assert settings.allowed_origins == ("https://amanah.example", "http://localhost:5173")


def test_a_trailing_slash_is_normalised_away() -> None:
    settings = make_settings(app_origin="https://amanah.example/, http://localhost:5173/")
    assert settings.allowed_origins == ("https://amanah.example", "http://localhost:5173")


@pytest.mark.parametrize(
    "origin",
    ["https://amanah.example/dashboard", "amanah.example", "ftp://amanah.example", ""],
)
def test_invalid_origin_is_rejected(origin: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(app_origin=origin)


def test_role_gates_are_enforced_unless_switched_off() -> None:
    """An environment that never sets the switch keeps its authorization checks."""
    assert make_settings().auth_enforce_role_gates is True
    assert make_settings(auth_enforce_role_gates=False).auth_enforce_role_gates is False


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(log_level="chatty")


def test_data_mode_defaults_to_fixture() -> None:
    assert make_settings().data_mode is DataMode.fixture


def test_optional_connectors_are_disabled_without_credentials() -> None:
    connectors = {connector.name: connector for connector in make_settings().connectors}

    assert set(connectors) == {"gemini", "youtube", "news", "reddit"}
    assert not any(connector.is_configured for connector in connectors.values())
    assert all(connector.purpose for connector in connectors.values())


def test_gemini_requires_both_a_key_and_a_model() -> None:
    key_only = make_settings(gemini_api_key="synthetic-key")
    complete = make_settings(gemini_api_key="synthetic-key", gemini_model="gemini-test")

    assert next(c for c in key_only.connectors if c.name == "gemini").is_configured is False
    assert next(c for c in complete.connectors if c.name == "gemini").is_configured is True


def test_missing_database_url_does_not_prevent_startup() -> None:
    assert make_settings(database_url=None).database_url is None


def test_secrets_are_not_exposed_by_string_conversion() -> None:
    settings: Settings = make_settings()

    assert TEST_JWT_SECRET not in repr(settings)
    assert TEST_JWT_SECRET not in str(settings)


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(supabase_jwt_secret="too-short")


@pytest.mark.parametrize("placeholder", [SECRET_PLACEHOLDER, "", "   "])
def test_placeholder_connector_credential_leaves_the_connector_disabled(
    placeholder: str,
) -> None:
    """Copying `.env.example` is the documented bootstrap path, so an unfilled
    value must not be mistaken for a real credential."""
    settings = make_settings(youtube_api_key=placeholder, news_api_key=placeholder)

    connectors = {connector.name: connector for connector in settings.connectors}
    assert connectors["youtube"].is_configured is False
    assert connectors["news"].is_configured is False


def test_placeholder_database_url_reports_as_unconfigured() -> None:
    settings = make_settings(
        database_url=f"postgresql://postgres:{SECRET_PLACEHOLDER}@localhost:5432/postgres"
    )

    assert settings.database_url is None


def test_a_real_credential_is_still_accepted() -> None:
    settings = make_settings(youtube_api_key="a-real-looking-synthetic-key")

    assert next(c for c in settings.connectors if c.name == "youtube").is_configured is True


def test_placeholder_in_a_required_variable_still_fails_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET_PLACEHOLDER)

    with pytest.raises(ConfigurationError):
        load_settings()
