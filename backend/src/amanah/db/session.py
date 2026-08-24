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
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from amanah.auth.principal import AuthenticatedUser
from amanah.domain.enums import HateType
from amanah.settings import Settings

logger = logging.getLogger(__name__)

#: Session setting PostgREST populates from a verified token. Reusing the exact
#: name means one predicate serves this service and a direct Supabase client.
JWT_CLAIMS_SETTING = "request.jwt.claims"


#: Postgres enum types this schema stores in *arrays*, mapped to the Python enum
#: that mirrors each one.
#:
#: psycopg knows nothing about a project-defined enum, so it hands back the raw
#: array literal (`'{derogation}'`) as a string. SQLAlchemy then treats that
#: string as the iterable it was told to expect and yields one element per
#: character, so `HateType(value)` is handed `'{'`. Registering the type makes
#: the driver return a real list. A *scalar* enum column is unaffected — it
#: arrives as text either way — so only the array-valued ones appear here.
ARRAY_ENUM_TYPES: tuple[tuple[str, type[StrEnum]], ...] = (("hate_type", HateType),)


def register_enum_types(engine: Engine) -> None:
    """Teach the driver this schema's enum types, once per pooled connection.

    Registration is per physical connection, so it hangs off the pool's connect
    event rather than running once at startup. A type that is absent — an older
    database, or a scratch one built before the enum existed — is skipped rather
    than raising: failing the connection here would be a far more confusing
    error than the one the caller would otherwise see.
    """
    import psycopg
    from psycopg.types.enum import EnumInfo, register_enum

    @event.listens_for(engine, "connect")
    def _register(dbapi_connection: psycopg.Connection[Any], _record: object) -> None:
        for type_name, python_enum in ARRAY_ENUM_TYPES:
            info = EnumInfo.fetch(dbapi_connection, type_name)
            if info is None:
                logger.debug("enum type absent, not registered", extra={"type_name": type_name})
                continue
            register_enum(info, dbapi_connection, python_enum)


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

    engine = create_engine(
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
    register_enum_types(engine)
    return engine


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
        """Yield a session whose every transaction is scoped to the caller.

        The identity is published from an `after_begin` hook rather than once up
        front. `SET LOCAL` lasts exactly as long as its transaction, so a service
        that commits mid-request — a run dispatch, a job transition — would
        otherwise continue on an anonymous connection and read nothing. Binding
        it to the start of each transaction means the scoping cannot be lost by
        committing.

        Anything uncommitted is rolled back on the way out, so a read never holds
        a transaction past the response and a failed write can never leave half
        of itself behind.
        """
        session = self._session_factory()
        publish = _identity_publisher(user)
        if publish is not None:
            event.listen(session, "after_begin", publish)
        try:
            yield session
        except SQLAlchemyError as exc:
            logger.error("database operation failed", exc_info=exc)
            raise DatabaseUnavailableError from exc
        finally:
            if publish is not None:
                event.remove(session, "after_begin", publish)
            session.rollback()
            session.close()

    def dispose(self) -> None:
        self._engine.dispose()


type _AfterBegin = Callable[[Session, SessionTransaction, Connection], None]


def _identity_publisher(user: AuthenticatedUser | None) -> _AfterBegin | None:
    """Build the hook that names the verified caller to each new transaction.

    `SET LOCAL` scopes the value to its transaction, so a pooled connection can
    never carry one request's identity into the next. The value is a JSON
    document built from typed fields, never from raw request text.

    Returns `None` for an unauthenticated session: nothing is published, so every
    owner-scoped predicate evaluates false, which is the safe direction to fail.
    """
    if user is None:
        return None
    claims = json.dumps({"sub": str(user.user_id), "app_metadata": {"role": user.role.value}})

    def publish(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
        del session, transaction
        connection.execute(
            text(f"SELECT set_config('{JWT_CLAIMS_SETTING}', :claims, true)"),
            {"claims": claims},
        )

    return publish
