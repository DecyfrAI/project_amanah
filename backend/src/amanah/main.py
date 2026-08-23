"""Application factory.

`create_app()` validates configuration before the server binds a port, so a
deployment with missing core settings fails to start rather than failing on its
first request.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from amanah.api import health
from amanah.api.errors import register_error_handlers
from amanah.api.security_headers import SecurityHeadersMiddleware
from amanah.api.v1.router import v1_router
from amanah.db.session import Database, create_database_engine
from amanah.observability.logging import configure_logging
from amanah.observability.request_context import REQUEST_ID_HEADER, RequestIdMiddleware
from amanah.settings import Settings, load_settings

logger = logging.getLogger(__name__)

API_TITLE = "Project Amanah API"
API_VERSION = "1.0.0"
API_DESCRIPTION = (
    "Authenticated research API for monitored Islamophobia and anti-Muslim hate data. "
    "Only /healthz and /readyz are unauthenticated."
)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the connection pool on startup and release it on shutdown.

    The pool is built lazily rather than at import, and its absence is not fatal:
    a service with no `DATABASE_URL` starts, reports `degraded` readiness, and
    refuses product reads with a `503`. Migrations are never run from here —
    they are a separate one-off process against the same artifact.
    """
    settings: Settings = app.state.settings
    if settings.database_url is None:
        app.state.database = None
        logger.warning("database not configured", extra={"impact": "product reads unavailable"})
    else:
        app.state.database = Database(create_database_engine(settings))
    try:
        yield
    finally:
        if app.state.database is not None:
            app.state.database.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application.

    Tests pass an explicit `Settings`; the server and CLI let it load from the
    process environment.
    """
    resolved = settings if settings is not None else load_settings()
    configure_logging(resolved.log_level)

    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        # No interactive documentation is mounted: the OpenAPI document is the
        # published contract, and serving Swagger UI would require relaxing the
        # response Content-Security-Policy to allow third-party scripts.
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )
    app.state.settings = resolved
    # Set before the lifespan runs so a request handled without one — as in an
    # ASGI test that never enters the lifespan — still finds the attribute.
    app.state.database = None

    register_error_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    # Added last, so it is the outermost middleware and every response — including
    # CORS rejections — carries a request identifier.
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    app.include_router(v1_router)

    disabled = [connector.name for connector in resolved.connectors if not connector.is_configured]
    logger.info(
        "application started",
        extra={
            "app_env": resolved.app_env,
            "data_mode": resolved.data_mode.value,
            "disabled_connectors": disabled,
        },
    )
    return app
