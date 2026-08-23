"""Migrations against an empty database, and the invariants they must leave behind (B-S3.8)."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, Engine, create_engine, inspect, text

from amanah.db.enums import ENUM_TYPES
from amanah.db.models import Base
from tests.db.scratch_database import (
    SKIP_REASON,
    configured_server_url,
    downgrade_to_base,
    scratch_database,
    upgrade_to_head,
)

#: Postgres truncates anything longer, which would silently rename a constraint
#: and break the migration that later tries to drop it by name.
MAX_IDENTIFIER_LENGTH = 63


def test_migrations_apply_to_an_empty_database_and_reverse_cleanly() -> None:
    """A fresh environment must be reachable from nothing, and reversible.

    This runs its own scratch database rather than reusing the session one,
    because it deliberately tears the schema back down to empty.
    """
    server_url = configured_server_url()
    if server_url is None:
        pytest.skip(SKIP_REASON)

    with scratch_database(server_url) as url:
        engine = create_engine(url)
        try:
            upgrade_to_head(url)
            after_upgrade = set(inspect(engine).get_table_names(schema="public"))
            assert {table.name for table in Base.metadata.sorted_tables} <= after_upgrade

            downgrade_to_base(url)
            after_downgrade = set(inspect(engine).get_table_names(schema="public"))
            # Only Alembic's own bookkeeping table may survive a full downgrade.
            assert after_downgrade == {"alembic_version"}
        finally:
            engine.dispose()


def test_every_model_table_exists(engine: Engine) -> None:
    present = set(inspect(engine).get_table_names(schema="public"))

    missing = {table.name for table in Base.metadata.sorted_tables} - present
    assert not missing, f"declared but not migrated: {sorted(missing)}"


def test_enum_types_match_the_controlled_vocabulary(connection: Connection) -> None:
    """The database and the published contract must not describe different values."""
    for python_enum, type_name in ENUM_TYPES:
        stored = connection.execute(
            text(
                "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = :name ORDER BY e.enumsortorder"
            ),
            {"name": type_name},
        ).scalars()
        assert list(stored) == [member.value for member in python_enum], type_name


def test_every_foreign_key_column_is_indexed(connection: Connection) -> None:
    """`rules/database.md`: Postgres does not index a foreign key for you, so a
    join or a cascading delete would fall back to a sequential scan."""
    unindexed = connection.execute(
        text(
            """
            SELECT conrelid::regclass::text AS table_name, a.attname AS column_name
            FROM pg_constraint c
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f'
              AND c.connamespace = 'public'::regnamespace
              AND NOT EXISTS (
                SELECT 1 FROM pg_index i
                WHERE i.indrelid = c.conrelid AND a.attnum = i.indkey[0]
              )
            ORDER BY 1, 2
            """
        )
    ).all()

    assert not unindexed, f"foreign keys without a leading index: {unindexed}"


def test_every_foreign_key_states_its_delete_behaviour(connection: Connection) -> None:
    """`NO ACTION` is the default nobody chose. Deletion behaviour is a decision."""
    undecided = connection.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "WHERE contype = 'f' AND connamespace = 'public'::regnamespace "
            "AND confdeltype = 'a' ORDER BY 1"
        )
    ).scalars()

    assert not list(undecided)


def test_identifiers_fit_within_the_postgres_limit(connection: Connection) -> None:
    over_length = connection.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE connamespace = 'public'::regnamespace "
            "AND length(conname) > :limit "
            "UNION ALL "
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
            "AND length(indexname) > :limit"
        ),
        {"limit": MAX_IDENTIFIER_LENGTH},
    ).scalars()

    assert not list(over_length)


def test_every_timestamp_column_carries_a_timezone(connection: Connection) -> None:
    naive = connection.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND data_type = 'timestamp without time zone' "
            "ORDER BY 1, 2"
        )
    ).all()

    assert not naive, f"timestamps without a timezone: {naive}"
