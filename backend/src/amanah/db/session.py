"""Engine and request-scoped sessions.

The engine is built once per application and only when a database is configured;
a service with no `DATABASE_URL` still starts, answers `/healthz`, and reports
`degraded` from `/readyz` rather than failing at import.

Every product request runs inside one transaction that first publishes the
verified caller into `request.jwt.claims`. That is the same session setting
Supabase's PostgREST sets from a validated access token, so the authenticated-safe
views and row-level-security policies evaluate the *server's* decision about who
is calling. A query issued without that step sees no owner-scoped rows at all,
which is the safe direction to fail in.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from amanah.auth.principal import AuthenticatedUser
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: Session setting PostgREST populates from a verified token. Reusing the exact
#: name means one predicate serves this service and a direct Supabase client.
JWT_CLAIMS_SETTING = "request.jwt.claims"


class DatabaseNotConfiguredError(RuntimeError):
    """No `DATABASE_URL` is set, so there is nothing to connect to."""


class DatabaseUnavailableError(RuntimeError):
    """The configured database could not be reached or the query failed.

    Carries no driver message: the caller receives a generic `503` and the real
    cause goes to the logs, because a driver error can name internal hosts.
    """


def _psycopg_url(url: str) -> str:
    """Pin psycopg 3 so a bare `postgresql://` URL does not select psycopg2."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def create_database_engine(settings: Settings) -> Engine:
    """Build the connection pool for the configured database.

    Both timeouts are explicit and configurable: `connect_timeout` bounds
    establishing a connection and `statement_timeout` bounds a query that has
    already started, so neither can hang a request indefinitely.
    """
    if settings.database_url is None:
        raise DatabaseNotConfiguredError

    return create_engine(
        _psycopg_url(settings.database_url.get_secret_value()),
        pool_size=settings.database_pool_size,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": settings.database_connect_timeout_seconds,
            "options": f"-c statement_timeout={settings.database_statement_timeout_ms}",
        },
    )


class Database:
    """Owns the engine and hands out request-scoped sessions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        return self._engine

    def check_connection(self) -> bool:
        """Probe the database for `/readyz`. Never raises."""
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.warning("database readiness probe failed", exc_info=exc)
            return False
        return True

    @contextmanager
    def session_for(self, user: AuthenticatedUser | None) -> Iterator[Session]:
        """Yield a session inside one transaction, scoped to the caller.

        Publishing the identity opens the transaction, which is what gives
        `SET LOCAL` something to be local to. Anything uncommitted is rolled back
        on the way out, so a read never holds a transaction past the response and
        a failed write can never leave half of itself behind.
        """
        session = self._session_factory()
        try:
            _publish_identity(session, user)
            yield session
        except SQLAlchemyError as exc:
            logger.error("database operation failed", exc_info=exc)
            raise DatabaseUnavailableError from exc
        finally:
            session.rollback()
            session.close()

    def dispose(self) -> None:
        self._engine.dispose()


def _publish_identity(session: Session, user: AuthenticatedUser | None) -> None:
    """Set the verified caller for the life of this transaction.

    `SET LOCAL` scopes the value to the transaction, so a pooled connection can
    never carry one request's identity into the next. The value is a JSON
    document built from typed fields, never from raw request text.
    """
    if user is None:
        # Nothing is published, so every owner-scoped predicate evaluates false.
        return
    claims = json.dumps({"sub": str(user.user_id), "app_metadata": {"role": user.role.value}})
    session.execute(
        text(f"SELECT set_config('{JWT_CLAIMS_SETTING}', :claims, true)"),
        {"claims": claims},
    )
