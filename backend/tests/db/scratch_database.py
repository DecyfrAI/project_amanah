"""Create and drop a throwaway database for schema and RLS tests.

`rules/testing.md` requires integration tests to run against a real dependency
and to be isolated at the data level. Every run creates its own empty database,
applies the migrations to it, and drops it afterwards, so no test can see data
another test left behind and the migrations are proven against an empty database
on every run.

The target server comes from `AMANAH_TEST_DATABASE_URL`. When it is unset the
database tests skip rather than silently passing.
"""

from __future__ import annotations

import os
import secrets
from argparse import Namespace
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

#: Server whose `postgres` maintenance database is used to create the scratch
#: database. Never a production target: the fixture creates and drops databases.
TEST_DATABASE_URL_VARIABLE = "AMANAH_TEST_DATABASE_URL"

SKIP_REASON = f"{TEST_DATABASE_URL_VARIABLE} is not set; database tests need a real Postgres server"

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _BACKEND_ROOT / "alembic.ini"


def configured_server_url() -> str | None:
    """The configured server URL, or `None` when database tests should skip."""
    url = os.environ.get(TEST_DATABASE_URL_VARIABLE, "").strip()
    return url or None


def with_driver(url: str) -> str:
    """Pin psycopg 3 so a bare `postgresql://` URL does not select psycopg2."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _with_database(url: str, database: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", parts.query, parts.fragment))


def _terminate_connections(connection: object, database: str) -> None:
    connection.execute(  # type: ignore[attr-defined]
        text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = :database AND pid <> pg_backend_pid()"
        ),
        {"database": database},
    )


@contextmanager
def scratch_database(server_url: str) -> Iterator[str]:
    """Yield the URL of an empty database, dropped when the block exits.

    The name is randomised so two concurrent runs against the same server cannot
    collide, and the drop runs even when the block raises.
    """
    database = f"amanah_test_{secrets.token_hex(8)}"
    admin_url = with_driver(_with_database(server_url, "postgres"))
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=None)
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
        try:
            yield with_driver(_with_database(server_url, database))
        finally:
            with admin_engine.connect() as connection:
                _terminate_connections(connection, database)
                connection.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
    finally:
        admin_engine.dispose()


def alembic_config(database_url: str) -> Config:
    """Alembic configuration pointed at one specific database.

    The URL travels as an `-x` argument, which is the same override the CLI
    offers. Nothing here mutates the process environment, so a test run cannot
    reach the developer's real `DATABASE_URL`.
    """
    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    config.cmd_opts = Namespace(x=[f"url={database_url}"])
    return config


def upgrade_to_head(database_url: str) -> None:
    """Apply every migration to an empty database."""
    command.upgrade(alembic_config(database_url), "head")


def downgrade_to_base(database_url: str) -> None:
    """Reverse every migration, leaving the database empty again."""
    command.downgrade(alembic_config(database_url), "base")
