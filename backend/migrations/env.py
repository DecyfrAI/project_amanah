"""Alembic environment.

Migrations run as a separate one-off process against the same release artifact,
never from application startup (`rules/backend.md`, Architecture). The connection
string comes from `DATABASE_URL` in the environment, or from `-x url=...` for a
scratch database in tests; it is never read from `alembic.ini`.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from amanah.db.models import Base

config = context.config

if config.config_file_name is not None:
    # `disable_existing_loggers` defaults to True, which would silence every
    # `amanah.*` logger already configured in this process. Migrations run as
    # their own process in deployment, but the test suite runs them in-process.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    """Resolve the target database, preferring an explicit `-x url=`."""
    override = context.get_x_argument(as_dictionary=True).get("url")
    if override:
        return str(override)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Pass it in the environment, or override it "
            "for one run with: alembic -x url=postgresql+psycopg://... upgrade head"
        )
    return url


def _psycopg_url(url: str) -> str:
    """Pin the driver so a bare `postgresql://` URL does not pick psycopg2."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    """Emit SQL to stdout for review without connecting."""
    context.configure(
        url=_psycopg_url(_database_url()),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live connection inside one transaction."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _psycopg_url(_database_url())
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
