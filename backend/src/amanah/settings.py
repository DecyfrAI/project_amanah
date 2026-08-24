"""Validated server configuration.

Configuration comes from the process environment only. There is exactly one
authority per value: no config file, no in-code default that shadows an
environment variable, and no lazy re-read at first use.

Core settings are validated at import of the application factory, so a
misconfigured deployment fails to start instead of failing on the first request.
Optional connector credentials are modelled explicitly: a missing key disables
that connector and nothing else.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Self
from urllib.parse import urlparse

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from amanah.domain.enums import DataMode

#: Supabase mints access tokens with this audience for signed-in users.
SUPABASE_ACCESS_TOKEN_AUDIENCE = "authenticated"  # noqa: S105 - a claim value, not a credential

#: RFC 7518 section 3.2 requires an HMAC key at least as long as the hash output.
#: A shorter signing secret weakens every token this service accepts, so it is
#: refused at startup rather than at the first request.
MINIMUM_JWT_SECRET_LENGTH = 32

_ALLOWED_ORIGIN_SCHEMES = frozenset({"http", "https"})

#: `.env.example` ships this marker wherever a real secret belongs, and copying
#: that file is the documented way to bootstrap an environment. A value still
#: carrying the marker was never filled in, so it is treated as absent rather
#: than handed to a provider as if it were a credential.
SECRET_PLACEHOLDER = "<REDACTED>"  # noqa: S105 - the marker for an absent value, not a secret


class ConfigurationError(RuntimeError):
    """Raised at startup when required configuration is missing or invalid.

    The message names the offending variables only. Values are never included,
    because several of them are secrets.
    """


class ConnectorConfiguration:
    """Whether an optional provider connector has the credentials it needs."""

    def __init__(self, name: str, purpose: str, *, is_configured: bool) -> None:
        self.name = name
        self.purpose = purpose
        self.is_configured = is_configured


class Settings(BaseSettings):
    """Server configuration read from environment variables.

    Load a local `.env` with `uv run --env-file .env ...`; the application itself
    reads the environment and nothing else.
    """

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    app_env: str = Field(default="development", description="Deployment environment name.")
    log_level: str = Field(default="INFO")
    data_mode: DataMode = Field(default=DataMode.fixture)

    app_origin: str = Field(
        description="Comma-separated browser origins allowed to call this API.",
    )
    supabase_url: str = Field(description="Base URL of the Supabase project.")
    supabase_jwt_secret: SecretStr = Field(
        min_length=MINIMUM_JWT_SECRET_LENGTH,
        description="Shared secret used to verify Supabase access tokens server-side.",
    )

    # Readiness dependency rather than a startup requirement: the process can
    # start and answer /healthz and /readyz without a database, but it is not
    # ready to serve product traffic until this is configured.
    database_url: SecretStr | None = Field(default=None)

    # Explicit, configurable bounds on both halves of a database call: how long
    # opening a connection may take, and how long a query that already started
    # may run. Neither may fall back to a driver default of "forever".
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    database_statement_timeout_ms: int = Field(default=5000, ge=100, le=60_000)
    database_pool_size: int = Field(default=5, ge=1, le=50)

    # Reviewed source and seed configuration. A directory rather than two paths,
    # because the two files are one reviewed artifact and must not drift apart.
    source_config_directory: Path | None = Field(
        default=None,
        description="Directory holding the reviewed sources and source-seeds YAML.",
    )

    # Bounds every outbound provider call shares. They are configuration rather
    # than constants so a slow provider can be accommodated without a release,
    # but none of them may be disabled: there is no "no timeout" value.
    http_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    http_read_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    http_total_timeout_seconds: float = Field(default=20.0, gt=0, le=180)
    http_max_response_bytes: int = Field(default=2_000_000, ge=1024, le=50_000_000)
    http_max_redirects: int = Field(default=3, ge=0, le=10)

    # Encrypts permitted original text at rest. Absent means original text is not
    # retained at all; it is never written as plaintext into the ciphertext
    # column. Base64 of exactly 32 bytes.
    content_encryption_key: SecretStr | None = Field(default=None)

    gemini_api_key: SecretStr | None = Field(default=None)
    gemini_model: str | None = Field(default=None)

    # Bounds every Gemini call shares (`spec.md` section 11.2). None of them may
    # be disabled, same reasoning as the generic HTTP bounds above: a Flash-class
    # model that hangs or free-runs its output is a real failure mode.
    gemini_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    gemini_max_retries: int = Field(default=2, ge=0, le=5)
    gemini_max_input_characters: int = Field(default=8000, ge=100, le=100_000)
    gemini_max_output_tokens: int = Field(default=1024, ge=16, le=8192)
    # Budgets are enforced by the caller-supplied tracker
    # (`amanah.ml.budgets`); these are its configured ceilings.
    gemini_per_run_token_budget: int = Field(default=200_000, ge=1)
    gemini_daily_token_budget: int = Field(default=2_000_000, ge=1)

    youtube_api_key: SecretStr | None = Field(default=None)
    news_api_key: SecretStr | None = Field(default=None)
    reddit_client_id: str | None = Field(default=None)
    reddit_client_secret: SecretStr | None = Field(default=None)

    @field_validator(
        "database_url",
        "content_encryption_key",
        "gemini_api_key",
        "gemini_model",
        "youtube_api_key",
        "news_api_key",
        "reddit_client_id",
        "reddit_client_secret",
        mode="before",
    )
    @classmethod
    def _unset_placeholder(cls, value: object) -> object:
        """Treat a blank or never-filled-in optional value as absent.

        Only optional values pass through here. A placeholder left in a required
        variable still fails startup, which is the correct outcome.
        """
        if isinstance(value, str) and (not value.strip() or SECRET_PLACEHOLDER in value):
            return None
        return value

    @field_validator("supabase_url")
    @classmethod
    def _check_supabase_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("must be an absolute https URL")
        return value.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return level

    @model_validator(mode="after")
    def _check_allowed_origins(self) -> Self:
        if not self.allowed_origins:
            raise ValueError("app_origin must list at least one origin")
        for origin in self.allowed_origins:
            parsed = urlparse(origin)
            if parsed.scheme not in _ALLOWED_ORIGIN_SCHEMES or not parsed.netloc:
                raise ValueError(f"app_origin entry is not a valid origin: {origin}")
            if parsed.path or parsed.query or parsed.fragment:
                raise ValueError(f"app_origin entry must not include a path: {origin}")
        return self

    @cached_property
    def allowed_origins(self) -> tuple[str, ...]:
        """Browser origins permitted by CORS."""
        return tuple(origin.strip() for origin in self.app_origin.split(",") if origin.strip())

    @cached_property
    def supabase_token_issuer(self) -> str:
        """Expected `iss` claim of a Supabase access token."""
        return f"{self.supabase_url}/auth/v1"

    @cached_property
    def connectors(self) -> tuple[ConnectorConfiguration, ...]:
        """Optional connectors and whether each one has usable credentials."""
        return (
            ConnectorConfiguration(
                "gemini",
                "Structured classification and cited narrative summaries.",
                is_configured=self.gemini_api_key is not None and bool(self.gemini_model),
            ),
            ConnectorConfiguration(
                "youtube",
                "Bounded video and comment collection through the official API.",
                is_configured=self.youtube_api_key is not None,
            ),
            ConnectorConfiguration(
                "news",
                "Headline collection from an approved news provider.",
                is_configured=self.news_api_key is not None,
            ),
            ConnectorConfiguration(
                "reddit",
                "Reserved; stays disabled until official research access is approved.",
                is_configured=self.reddit_client_id is not None
                and self.reddit_client_secret is not None,
            ),
        )


def load_settings() -> Settings:
    """Read and validate settings, or fail with a safe, actionable message."""
    try:
        return Settings()  # type: ignore[call-arg]  # values come from the environment
    except ValidationError as exc:
        variables = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
        raise ConfigurationError(
            "Invalid or missing required configuration: " + ", ".join(variables)
        ) from exc
