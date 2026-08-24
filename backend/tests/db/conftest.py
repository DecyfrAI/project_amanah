"""Fixtures for tests that need a real Postgres.

One scratch database is created for the whole session, the migrations are applied
to it from empty, and it is dropped at the end. Every test starts from an empty
set of product tables, so no test depends on another's data or on execution
order.

Set `AMANAH_TEST_DATABASE_URL` to a Postgres server these tests may create and
drop databases on. Without it they skip, and the skip is reported rather than
passing silently.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import Connection, Engine, create_engine, text

from amanah.db.models import Base
from amanah.db.session import register_enum_types
from amanah.domain.enums import Role
from tests.db.scratch_database import (
    SKIP_REASON,
    configured_server_url,
    scratch_database,
    upgrade_to_head,
)

#: Emptied before every test. `TRUNCATE` rather than `DELETE` so the append-only
#: triggers, which exist precisely to refuse row deletion, do not block cleanup.
_PRODUCT_TABLES = tuple(table.name for table in Base.metadata.sorted_tables)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    server_url = configured_server_url()
    if server_url is None:
        pytest.skip(SKIP_REASON)
    with scratch_database(server_url) as url:
        upgrade_to_head(url)
        yield url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    created = create_engine(database_url)
    # The same driver registration the application engine performs. Without it
    # these tests would read this schema's enum arrays differently from the way
    # the service does, and would therefore prove nothing about it.
    register_enum_types(created)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture(autouse=True)
def clean_database(engine: Engine) -> Iterator[None]:
    """Leave the product tables empty before and after every test."""
    _truncate(engine)
    yield
    _truncate(engine)


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    """A connection whose work is rolled back when the test finishes."""
    with engine.connect() as active:
        transaction = active.begin()
        try:
            yield active
        finally:
            transaction.rollback()


def _truncate(engine: Engine) -> None:
    statement = (
        "TRUNCATE TABLE "
        + ", ".join(f"public.{name}" for name in _PRODUCT_TABLES)
        + " RESTART IDENTITY CASCADE"
    )
    with engine.begin() as active:
        active.execute(text(statement))


def act_as(connection: Connection, role: str, claims: dict[str, Any] | None = None) -> None:
    """Continue this transaction as a Supabase database role.

    `SET LOCAL ROLE` is what makes a row-level-security test real: the statements
    that follow are planned and executed with that role's privileges and
    policies, exactly as a request arriving through PostgREST would be.
    """
    connection.execute(text(f"SET LOCAL ROLE {role}"))
    connection.execute(
        text("SELECT set_config('request.jwt.claims', :claims, true)"),
        {"claims": json.dumps(claims) if claims is not None else ""},
    )


def claims_for(user_id: UUID, role: Role = Role.registered_user) -> dict[str, Any]:
    """The claim shape Supabase issues for a signed-in user."""
    return {"sub": str(user_id), "role": "authenticated", "app_metadata": {"role": role.value}}
