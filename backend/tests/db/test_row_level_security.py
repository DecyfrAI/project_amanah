"""The row-level-security boundary, exercised as the database roles themselves (B-S3.7, B-S3.8).

Each test does `SET LOCAL ROLE` and then queries, so it runs with the same
privileges and policies a request arriving through Supabase's PostgREST would.
Anonymous denial is checked for every table and every view, not for a sample,
because one forgotten grant is the whole hole.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DatabaseError

from amanah.db.models import Base
from amanah.domain.enums import PublicationStatus, Role
from tests.db import factories
from tests.db.conftest import act_as, claims_for

PRODUCT_TABLES = tuple(table.name for table in Base.metadata.sorted_tables)


def _authenticated_views(connection: Connection) -> tuple[str, ...]:
    names = connection.execute(
        text(
            "SELECT table_name FROM information_schema.views "
            "WHERE table_schema = 'public' AND table_name LIKE 'authenticated%' ORDER BY 1"
        )
    ).scalars()
    return tuple(str(name) for name in names)


def test_the_projections_exist(connection: Connection) -> None:
    """Guards the parametrised denial tests below: if the views vanished, those
    would pass vacuously."""
    assert len(_authenticated_views(connection)) >= 10


@pytest.mark.parametrize("table", PRODUCT_TABLES)
def test_anonymous_callers_cannot_read_any_product_table(
    connection: Connection, table: str
) -> None:
    act_as(connection, "anon")

    with pytest.raises(DatabaseError):
        connection.execute(text(f"SELECT * FROM public.{table} LIMIT 1"))


def test_anonymous_callers_cannot_read_any_authenticated_projection(
    connection: Connection,
) -> None:
    views = _authenticated_views(connection)
    act_as(connection, "anon")

    for view in views:
        # Each attempt aborts the transaction, so it runs inside its own
        # savepoint and the role set before the loop survives the rollback.
        savepoint = connection.begin_nested()
        with pytest.raises(DatabaseError):
            connection.execute(text(f"SELECT * FROM public.{view} LIMIT 1"))
        savepoint.rollback()


def test_anonymous_callers_cannot_call_the_identity_functions(connection: Connection) -> None:
    act_as(connection, "anon")

    with pytest.raises(DatabaseError):
        connection.execute(text("SELECT public.amanah_current_user_id()"))


@pytest.mark.parametrize("table", PRODUCT_TABLES)
def test_authenticated_callers_cannot_read_base_tables_directly(
    connection: Connection, table: str
) -> None:
    """The projections are the only relations `authenticated` may read. That is
    what makes column safety structural: a raw column is unreachable, not merely
    unselected."""
    act_as(connection, "authenticated", claims_for(uuid4()))

    with pytest.raises(DatabaseError):
        connection.execute(text(f"SELECT * FROM public.{table} LIMIT 1"))


def test_row_level_security_is_enabled_and_forced_on_every_product_table(
    connection: Connection,
) -> None:
    """`FORCE` matters: without it the table owner is exempt from its own policies."""
    unprotected = connection.execute(
        text(
            "SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' "
            "AND relname <> 'alembic_version' "
            "AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity) ORDER BY 1"
        )
    ).scalars()

    assert not list(unprotected)


def test_no_policy_grants_anything_to_the_anonymous_role(connection: Connection) -> None:
    anonymous_policies = connection.execute(
        text(
            "SELECT policyname FROM pg_policies "
            "WHERE schemaname = 'public' AND 'anon' = ANY (roles) ORDER BY 1"
        )
    ).scalars()

    assert not list(anonymous_policies)


def test_an_authenticated_reader_sees_items_through_the_projection(
    connection: Connection,
) -> None:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    factories.insert_prediction(connection, content_item_id=item_id)

    act_as(connection, "authenticated", claims_for(uuid4()))
    rows = connection.execute(text("SELECT id FROM public.authenticated_items")).scalars().all()

    assert [str(value) for value in rows] == [str(item_id)]


def test_a_session_without_a_verified_identity_sees_no_items(connection: Connection) -> None:
    """The projection refuses rows when no identity was published, so a query
    issued without the per-request scoping step fails closed."""
    source_id = factories.insert_source(connection)
    factories.insert_content_item(connection, source_id=source_id)

    act_as(connection, "authenticated", claims=None)
    rows = connection.execute(text("SELECT id FROM public.authenticated_items")).all()

    assert rows == []


def test_a_user_reads_only_their_own_contribution_history(connection: Connection) -> None:
    owner = uuid4()
    stranger = uuid4()
    factories.insert_contribution_event(connection, user_id=owner, public_message="Mine.")
    factories.insert_contribution_event(connection, user_id=stranger, public_message="Theirs.")

    act_as(connection, "authenticated", claims_for(owner))
    messages = (
        connection.execute(
            text("SELECT public_message FROM public.authenticated_contribution_events")
        )
        .scalars()
        .all()
    )

    assert messages == ["Mine."]


def test_a_reviewer_does_not_reach_another_user_history_through_an_owner_scoped_read(
    connection: Connection,
) -> None:
    """Reviewers reach records through the review queue. Elevating a role must
    not silently widen an owner-scoped projection."""
    owner = uuid4()
    reviewer = uuid4()
    factories.insert_contribution_event(connection, user_id=owner)

    act_as(connection, "authenticated", claims_for(reviewer, Role.reviewer))
    rows = connection.execute(text("SELECT id FROM public.authenticated_contribution_events")).all()

    assert rows == []


def test_a_user_reads_only_their_own_profile(connection: Connection) -> None:
    owner = uuid4()
    stranger = uuid4()
    factories.insert_user_profile(connection, user_id=owner)
    factories.insert_user_profile(connection, user_id=stranger)

    act_as(connection, "authenticated", claims_for(owner))
    rows = (
        connection.execute(text("SELECT user_id FROM public.authenticated_user_profile"))
        .scalars()
        .all()
    )

    assert [str(value) for value in rows] == [str(owner)]


def test_only_published_resources_reach_a_base_role_reader(connection: Connection) -> None:
    factories.insert_resource_entry(
        connection, title="Reviewed", status=PublicationStatus.published
    )
    factories.insert_resource_entry(connection, title="Draft", status=PublicationStatus.draft)
    factories.insert_resource_entry(connection, title="Archived", status=PublicationStatus.archived)

    act_as(connection, "authenticated", claims_for(uuid4()))
    titles = (
        connection.execute(text("SELECT title FROM public.authenticated_resources")).scalars().all()
    )

    assert titles == ["Reviewed"]
