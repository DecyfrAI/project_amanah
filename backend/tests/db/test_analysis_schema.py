"""Migration `0005`: sampling strata and the image corpus (B-S15.9, B-S26.7).

Runs against a real Postgres. The constraints here are the ones that make the
guarantees real rather than conventional: a stratum that is part of a bucket's
identity, an image table with no column for bytes, and a projection that cannot
leak a storage path.

Requires `AMANAH_TEST_DATABASE_URL`; without it the whole module skips and the
skip is reported.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from amanah.domain.enums import (
    InferenceStatus,
    PublicationStatus,
    Relevance,
    SamplingStratum,
    Stance,
)
from tests.db import factories
from tests.db.conftest import act_as, claims_for
from tests.db.factories import BASE_TIME

# --- Sampling strata -------------------------------------------------------


def test_two_strata_may_share_a_bucket_position_without_colliding(
    connection: Connection,
) -> None:
    """The stratum is part of the identity, so the two stay separate rows.

    Without it the enriched sample would upsert onto the ordinary-monitoring row
    and the two would become one figure — a purposive sample published as if it
    described everything.
    """
    source_id = factories.insert_source(connection)

    enriched = factories.insert_metric_bucket(
        connection, source_id=source_id, sampling_stratum=SamplingStratum.enriched
    )
    ordinary = factories.insert_metric_bucket(
        connection, source_id=source_id, sampling_stratum=SamplingStratum.ordinary_monitoring
    )

    assert enriched != ordinary


def test_the_same_stratum_at_the_same_position_still_collides(
    connection: Connection,
) -> None:
    """Idempotency is preserved: recomputing one bucket does not add a second."""
    source_id = factories.insert_source(connection)
    factories.insert_metric_bucket(
        connection, source_id=source_id, sampling_stratum=SamplingStratum.enriched
    )

    with pytest.raises(IntegrityError):
        factories.insert_metric_bucket(
            connection, source_id=source_id, sampling_stratum=SamplingStratum.enriched
        )


def test_an_existing_bucket_defaults_to_ordinary_monitoring(connection: Connection) -> None:
    """Rows written before the column existed came from unseeded collection."""
    source_id = factories.insert_source(connection)
    connection.execute(
        text(
            "INSERT INTO public.metric_buckets "
            "(metric_key, source_id, interval, bucket_start, filter_version, "
            " sampling_disclosure) "
            "VALUES ('likely_anti_muslim_rate', :source_id, 'daily', :start, 'f1', 'disclosure')"
        ),
        {"source_id": source_id, "start": BASE_TIME},
    )

    stored = connection.execute(
        text("SELECT sampling_stratum FROM public.metric_buckets WHERE source_id = :source_id"),
        {"source_id": source_id},
    ).scalar_one()

    assert stored == SamplingStratum.ordinary_monitoring.value


def test_the_metric_projection_exposes_the_stratum(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    factories.insert_metric_bucket(
        connection, source_id=source_id, sampling_stratum=SamplingStratum.enriched
    )
    user_id = factories.insert_user_profile(connection, user_id=uuid4())

    act_as(connection, "authenticated", claims_for(user_id))
    stored = connection.execute(
        text("SELECT sampling_stratum FROM public.authenticated_metric_buckets")
    ).scalar_one()

    assert stored == SamplingStratum.enriched.value


def test_an_insight_snapshot_holds_a_full_digest(connection: Connection) -> None:
    """`data_version` carries a 64-character bundle hash, not a version label."""
    digest = "a" * 64
    connection.execute(
        text(
            "INSERT INTO public.insight_snapshots "
            "(filter_hash, data_version, model_name, prompt_version, output) "
            "VALUES (:filter_hash, :data_version, 'gemini-test', 'summarize-1', '{}'::jsonb)"
        ),
        {"filter_hash": "f" * 64, "data_version": digest},
    )

    stored = connection.execute(
        text("SELECT data_version FROM public.insight_snapshots")
    ).scalar_one()

    assert stored == digest


# --- Image corpus ----------------------------------------------------------


def test_the_image_tables_have_no_column_for_bytes(connection: Connection) -> None:
    """ADR 0007: object storage holds the bytes, Postgres holds the metadata."""
    for table in ("image_examples", "image_classifications"):
        columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table"
                ),
                {"table": table},
            ).scalars()
        )
        for forbidden in ("image_bytes", "image_base64", "content", "bytes", "data"):
            assert forbidden not in columns, f"{table}.{forbidden}"


def test_an_image_example_requires_alt_text(connection: Connection) -> None:
    package_id = factories.insert_dataset_package(connection)

    with pytest.raises(IntegrityError):
        factories.insert_image_example(connection, dataset_package_id=package_id, alt_text="   ")


def test_an_unreviewed_media_type_is_refused(connection: Connection) -> None:
    package_id = factories.insert_dataset_package(connection)

    with pytest.raises(IntegrityError):
        factories.insert_image_example(
            connection, dataset_package_id=package_id, mime_type="image/svg+xml"
        )


def test_one_row_per_file_per_package(connection: Connection) -> None:
    package_id = factories.insert_dataset_package(connection)
    factories.insert_image_example(connection, dataset_package_id=package_id)

    with pytest.raises(IntegrityError):
        factories.insert_image_example(connection, dataset_package_id=package_id)


def test_the_same_row_id_in_two_packages_does_not_collide(connection: Connection) -> None:
    first = factories.insert_dataset_package(connection, name="pack-a")
    second = factories.insert_dataset_package(connection, name="pack-b")

    left = factories.insert_image_example(connection, dataset_package_id=first)
    right = factories.insert_image_example(
        connection, dataset_package_id=second, storage_path="image-examples/other/row-1.png"
    )

    assert left != right


def test_an_unsuccessful_classification_may_not_claim_hate(connection: Connection) -> None:
    """The same rule `predictions` carries: a non-answer is not a finding."""
    package_id = factories.insert_dataset_package(connection)
    example_id = factories.insert_image_example(connection, dataset_package_id=package_id)

    with pytest.raises(IntegrityError):
        factories.insert_image_classification(
            connection,
            image_example_id=example_id,
            stance=Stance.likely_anti_muslim,
            inference_status=InferenceStatus.deferred,
        )


def test_a_classification_is_idempotent_for_its_version_triple(
    connection: Connection,
) -> None:
    package_id = factories.insert_dataset_package(connection)
    example_id = factories.insert_image_example(connection, dataset_package_id=package_id)
    factories.insert_image_classification(connection, image_example_id=example_id)

    with pytest.raises(IntegrityError):
        factories.insert_image_classification(connection, image_example_id=example_id)


def test_a_new_prompt_version_adds_history_rather_than_replacing_it(
    connection: Connection,
) -> None:
    package_id = factories.insert_dataset_package(connection)
    example_id = factories.insert_image_example(connection, dataset_package_id=package_id)
    first = factories.insert_image_classification(connection, image_example_id=example_id)

    second = factories.insert_image_classification(
        connection, image_example_id=example_id, prompt_version="classify-image-2"
    )

    assert first != second
    remaining = connection.execute(
        text("SELECT count(*) FROM public.image_classifications WHERE image_example_id = :id"),
        {"id": example_id},
    ).scalar_one()
    assert remaining == 2


# --- Access boundary -------------------------------------------------------


def test_the_image_projection_never_exposes_a_storage_path(connection: Connection) -> None:
    columns = set(
        connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'authenticated_image_examples'"
            )
        ).scalars()
    )

    assert "storage_path" not in columns


def test_a_verified_reader_sees_published_entries_through_the_projection(
    connection: Connection,
) -> None:
    package_id = factories.insert_dataset_package(connection)
    example_id = factories.insert_image_example(connection, dataset_package_id=package_id)
    factories.insert_image_classification(connection, image_example_id=example_id)
    user_id = factories.insert_user_profile(connection, user_id=uuid4())

    act_as(connection, "authenticated", claims_for(user_id))
    row = connection.execute(
        text(
            "SELECT id, stance, annotation_hate_types, predicted_hate_types "
            "FROM public.authenticated_image_examples"
        )
    ).one()

    assert row.id == example_id
    assert row.stance == Stance.likely_anti_muslim.value
    # The dataset's own label and this product's finding stay in separate columns.
    assert row.annotation_hate_types == ["derogation"]
    assert row.predicted_hate_types == ["derogation"]


def test_a_draft_entry_never_reaches_a_reader(connection: Connection) -> None:
    package_id = factories.insert_dataset_package(connection)
    factories.insert_image_example(
        connection,
        dataset_package_id=package_id,
        publication_status=PublicationStatus.draft,
    )
    user_id = factories.insert_user_profile(connection, user_id=uuid4())

    act_as(connection, "authenticated", claims_for(user_id))
    rows = connection.execute(text("SELECT id FROM public.authenticated_image_examples")).all()

    assert rows == []


def test_an_unclassified_entry_reports_absent_labels_not_safe_ones(
    connection: Connection,
) -> None:
    """Absence means "not analysed". It never means "found to be safe"."""
    package_id = factories.insert_dataset_package(connection)
    factories.insert_image_example(connection, dataset_package_id=package_id)
    user_id = factories.insert_user_profile(connection, user_id=uuid4())

    act_as(connection, "authenticated", claims_for(user_id))
    row = connection.execute(
        text("SELECT relevance, stance, score FROM public.authenticated_image_examples")
    ).one()

    assert row.relevance is None
    assert row.stance is None
    assert row.score is None


def test_an_unsuccessful_classification_is_not_projected_as_current(
    connection: Connection,
) -> None:
    package_id = factories.insert_dataset_package(connection)
    example_id = factories.insert_image_example(connection, dataset_package_id=package_id)
    factories.insert_image_classification(
        connection,
        image_example_id=example_id,
        stance=Stance.uncertain,
        relevance=Relevance.uncertain,
        hate_types=(),
        severity=0,
        inference_status=InferenceStatus.provider_failure,
    )
    user_id = factories.insert_user_profile(connection, user_id=uuid4())

    act_as(connection, "authenticated", claims_for(user_id))
    row = connection.execute(text("SELECT stance FROM public.authenticated_image_examples")).one()

    assert row.stance is None


# Anonymous denial for the two new tables and the new view is already covered:
# `test_row_level_security.py` parametrises over `Base.metadata.sorted_tables` and
# enumerates every `authenticated%` view, so both are picked up automatically.
# Repeating it here would be duplication that could drift.


def test_a_base_role_reader_cannot_reach_the_image_tables_directly(
    connection: Connection,
) -> None:
    """The projection is the only way in, which is what keeps the path unreachable."""
    user_id = factories.insert_user_profile(connection, user_id=uuid4())
    act_as(connection, "authenticated", claims_for(user_id))

    with pytest.raises(DBAPIError):
        connection.execute(text("SELECT storage_path FROM public.image_examples"))
