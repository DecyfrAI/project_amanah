"""What the authenticated-safe projections may and may not contain (B-S3.6, B-S5.6).

Two things are checked. First, that the read handles in `amanah.db.views` still
describe the real views, so a repository cannot be selecting a column the view
stopped having. Second — the point of the whole design — that no projection has
a column for raw text, encrypted text, a private storage key, a provider payload,
or a provider-side identifier that could re-identify an author.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Connection, Table, text

from amanah.db.views import (
    FORBIDDEN_PROJECTION_COLUMNS,
    authenticated_background_jobs,
    authenticated_collection_runs,
    authenticated_items,
    authenticated_managed_resources,
    authenticated_metric_buckets,
    authenticated_news,
    authenticated_research_report_audit_events,
    authenticated_research_reports,
    authenticated_resource_audit_events,
    authenticated_resources,
    authenticated_source_status,
)
from amanah.domain.enums import Role
from tests.db import factories
from tests.db.conftest import act_as, claims_for

DECLARED_PROJECTIONS: tuple[Table, ...] = (
    authenticated_items,
    authenticated_metric_buckets,
    authenticated_source_status,
    authenticated_resources,
    authenticated_managed_resources,
    authenticated_resource_audit_events,
    authenticated_research_reports,
    authenticated_research_report_audit_events,
    authenticated_news,
    authenticated_collection_runs,
    authenticated_background_jobs,
)


def _view_columns(connection: Connection, view: str) -> set[str]:
    return set(
        connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :view"
            ),
            {"view": view},
        ).scalars()
    )


def test_declared_projections_match_the_real_views(connection: Connection) -> None:
    for table in DECLARED_PROJECTIONS:
        actual = _view_columns(connection, table.name)
        declared = {column.name for column in table.columns}
        assert declared == actual, f"{table.name}: declared {declared ^ actual} differs"


def test_no_projection_exposes_raw_content_or_an_author_identifier(
    connection: Connection,
) -> None:
    views = connection.execute(
        text(
            "SELECT table_name FROM information_schema.views "
            "WHERE table_schema = 'public' AND table_name LIKE 'authenticated%'"
        )
    ).scalars()

    for view in views:
        leaked = _view_columns(connection, str(view)) & FORBIDDEN_PROJECTION_COLUMNS
        assert not leaked, f"{view} exposes {sorted(leaked)}"


def test_the_item_projection_omits_the_stored_raw_columns(connection: Connection) -> None:
    """The row genuinely holds encrypted text, model input, and a storage key;
    the projection simply has nowhere to put them."""
    source_id = factories.insert_source(connection)
    factories.insert_content_item(
        connection,
        source_id=source_id,
        normalized_text="model input that must not surface",
        raw_object_key="private/object/key",
    )

    act_as(connection, "authenticated", claims_for(uuid4()))
    row = connection.execute(text("SELECT * FROM public.authenticated_items")).mappings().one()

    serialized = " ".join(str(value) for value in row.values())
    assert "model input that must not surface" not in serialized
    assert "private/object/key" not in serialized


def test_the_connector_projection_carries_no_provider_failure_detail(
    connection: Connection,
) -> None:
    """A connector may be failing; why it is failing stays in the logs."""
    factories.insert_source(connection, safe_warning="Coverage is partial for this window.")

    act_as(connection, "authenticated", claims_for(uuid4()))
    row = (
        connection.execute(text("SELECT * FROM public.authenticated_source_status"))
        .mappings()
        .one()
    )

    assert row["safe_warning"] == "Coverage is partial for this window."
    # `source_key` is the stable configuration identifier, not a credential.
    credential_shaped = {"api_key", "secret", "token", "password", "connection_string", "dsn"}
    assert not credential_shaped & set(row)


def test_a_datapack_item_publishes_not_applicable_while_keeping_its_lineage(
    connection: Connection,
) -> None:
    """`N/A` is a display value. It must not erase which dataset a row came from."""
    source_id = factories.insert_open_datapack_source(connection)
    package_id = factories.insert_dataset_package(
        connection, provider="synthetic-provider", name="synthetic-dataset", version="1.0.0"
    )
    factories.insert_content_item(
        connection,
        source_id=source_id,
        dataset_package_id=package_id,
        dataset_row_id="row-42",
    )

    act_as(connection, "authenticated", claims_for(uuid4()))
    row = connection.execute(text("SELECT * FROM public.authenticated_items")).mappings().one()

    assert row["platform"] == "not_applicable"
    assert row["source_name"] == "N/A"
    assert row["dataset_provider"] == "synthetic-provider"
    assert row["dataset_name"] == "synthetic-dataset"
    assert row["dataset_version"] == "1.0.0"


def test_the_item_projection_shows_the_newest_successful_prediction(
    connection: Connection,
) -> None:
    """Superseded executions stay in the table as history; the projection shows
    the one that currently stands."""
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    factories.insert_prediction(
        connection,
        content_item_id=item_id,
        model_version="v1",
        score=0.10,
        created_at=factories.days_after(-2),
    )
    factories.insert_prediction(
        connection,
        content_item_id=item_id,
        model_version="v2",
        score=0.90,
        created_at=factories.days_after(-1),
    )

    act_as(connection, "authenticated", claims_for(uuid4()))
    row = connection.execute(text("SELECT * FROM public.authenticated_items")).mappings().one()

    assert row["model_version"] == "v2"
    assert row["score"] == 0.90


def test_a_failed_inference_does_not_become_the_item_label(connection: Connection) -> None:
    """A provider failure leaves the item unclassified rather than mislabelled."""
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    factories.insert_prediction(
        connection,
        content_item_id=item_id,
        inference_status=factories.InferenceStatus.provider_failure,
    )

    act_as(connection, "authenticated", claims_for(uuid4()))
    row = connection.execute(text("SELECT * FROM public.authenticated_items")).mappings().one()

    assert row["prediction_id"] is None
    assert row["relevance"] is None


def test_the_news_projection_cannot_carry_a_classification(connection: Connection) -> None:
    """Reconciliation G5. An ingested article coincides with a window; it is not
    an Amanah finding, and the projection has nowhere to say otherwise."""
    columns = _view_columns(connection, "authenticated_news")

    classification = {
        "relevance",
        "stance",
        "hate_types",
        "severity",
        "score",
        "confidence_tier",
        "review_state",
        "requires_review",
        "rationale",
        "prediction_id",
    }
    assert not columns & classification


def test_the_run_projection_hides_the_queue_from_a_non_administrator(
    connection: Connection,
) -> None:
    """Operational state is administrator-only, enforced by the view itself and
    not only by the route that reads it."""
    source_id = factories.insert_source(connection)
    factories.insert_collection_run(connection, source_id=source_id)

    act_as(connection, "authenticated", claims_for(uuid4(), Role.registered_user))
    rows = connection.execute(text("SELECT id FROM public.authenticated_collection_runs")).all()

    assert rows == []


def test_the_run_projection_shows_an_administrator_its_runs(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    factories.insert_collection_run(connection, source_id=source_id)

    act_as(connection, "authenticated", claims_for(uuid4(), Role.administrator))
    rows = connection.execute(
        text("SELECT id, status FROM public.authenticated_collection_runs")
    ).all()

    assert len(rows) == 1
