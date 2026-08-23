"""The constraints `spec.md` section 14.6 requires, proved against Postgres (B-S3.3, B-S3.8).

Each test does the thing the constraint exists to prevent and expects the
database — not the application — to refuse it.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from amanah.domain.enums import ApprovalStatus, InferenceStatus, PublicationStatus, Stance
from tests.db import factories


def test_one_row_per_source_item(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    factories.insert_content_item(connection, source_id=source_id, source_item_id="shared")

    with pytest.raises(IntegrityError):
        factories.insert_content_item(connection, source_id=source_id, source_item_id="shared")


def test_the_same_datapack_row_cannot_be_imported_twice(connection: Connection) -> None:
    source_id = factories.insert_open_datapack_source(connection)
    package_id = factories.insert_dataset_package(connection)
    factories.insert_content_item(
        connection,
        source_id=source_id,
        dataset_package_id=package_id,
        dataset_row_id="row-1",
    )

    with pytest.raises(IntegrityError):
        factories.insert_content_item(
            connection,
            source_id=source_id,
            dataset_package_id=package_id,
            dataset_row_id="row-1",
        )


def test_the_same_row_id_in_two_packages_is_not_a_duplicate(connection: Connection) -> None:
    """Row identifiers are only unique inside their package. Collapsing `row-1`
    across two datasets would silently discard one of them."""
    source_id = factories.insert_open_datapack_source(connection)
    first = factories.insert_dataset_package(connection, name="dataset-a")
    second = factories.insert_dataset_package(connection, name="dataset-b")

    factories.insert_content_item(
        connection, source_id=source_id, dataset_package_id=first, dataset_row_id="row-1"
    )
    factories.insert_content_item(
        connection, source_id=source_id, dataset_package_id=second, dataset_row_id="row-1"
    )

    stored = connection.execute(
        text("SELECT count(*) FROM public.content_items WHERE dataset_row_id = 'row-1'")
    ).scalar_one()
    assert stored == 2


def test_dataset_provenance_is_all_or_nothing(connection: Connection) -> None:
    """A row may not claim a package without naming the row it came from."""
    source_id = factories.insert_open_datapack_source(connection)
    package_id = factories.insert_dataset_package(connection)

    with pytest.raises(IntegrityError):
        factories.insert_content_item(
            connection,
            source_id=source_id,
            dataset_package_id=package_id,
            dataset_row_id=None,
        )


def test_only_one_controlled_open_datapack_source_may_exist(connection: Connection) -> None:
    """`N/A` has to mean one well-known record, not a magic string per import."""
    factories.insert_open_datapack_source(connection)

    with pytest.raises(IntegrityError):
        factories.insert_source(
            connection,
            source_key="open_datapack_2",
            kind=factories.SourceKind.open_datapack,
            platform=factories.PublicPlatform.not_applicable,
            name="N/A",
        )


def test_one_prediction_per_item_and_version_triple(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    factories.insert_prediction(connection, content_item_id=item_id)

    with pytest.raises(IntegrityError):
        factories.insert_prediction(connection, content_item_id=item_id)


def test_a_new_model_version_adds_history_rather_than_replacing_it(
    connection: Connection,
) -> None:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    factories.insert_prediction(connection, content_item_id=item_id, model_version="v1")
    factories.insert_prediction(connection, content_item_id=item_id, model_version="v2")

    stored = connection.execute(
        text("SELECT count(*) FROM public.predictions WHERE content_item_id = :id"),
        {"id": item_id},
    ).scalar_one()
    assert stored == 2


def test_a_failed_inference_may_not_claim_anti_muslim_rhetoric(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)

    with pytest.raises(IntegrityError):
        factories.insert_prediction(
            connection,
            content_item_id=item_id,
            stance=Stance.likely_anti_muslim,
            inference_status=InferenceStatus.provider_failure,
        )


def test_a_prediction_score_stays_within_zero_and_one(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)

    with pytest.raises(IntegrityError):
        factories.insert_prediction(connection, content_item_id=item_id, score=1.4)


def test_a_seed_entry_is_identified_by_registry_key_and_config_version(
    connection: Connection,
) -> None:
    source_id = factories.insert_source(connection)
    factories.insert_seed_entry(connection, source_id=source_id, config_version="v1")
    # A new configuration version of the same registry entry is a different row.
    factories.insert_seed_entry(connection, source_id=source_id, config_version="v2")

    with pytest.raises(IntegrityError):
        factories.insert_seed_entry(connection, source_id=source_id, config_version="v2")


def test_a_seed_entry_needs_a_positive_item_cap(connection: Connection) -> None:
    source_id = factories.insert_source(connection)

    with pytest.raises(IntegrityError):
        factories.insert_seed_entry(connection, source_id=source_id, item_cap=0)


def test_an_approved_dataset_package_names_its_approver(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        factories.insert_dataset_package(
            connection, approval_status=ApprovalStatus.approved, approved_by=None
        )


def test_a_dataset_package_records_a_real_file_hash(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO public.dataset_packages "
                "(provider, name, version, landing_page_url, license_id, permitted_uses, "
                " retrieved_at, file_sha256, schema_mapping_version) "
                "VALUES ('p', 'n', 'v', 'https://example.test', 'CC0', 'research', now(), "
                "'not-a-hash', 'v1')"
            )
        )


def test_metric_bucket_counts_must_nest(connection: Connection) -> None:
    """A stored bucket must not be able to produce a rate above one."""
    source_id = factories.insert_source(connection)

    with pytest.raises(IntegrityError):
        factories.insert_metric_bucket(
            connection, source_id=source_id, relevant_count=2, likely_hate_count=5
        )


def test_one_metric_bucket_per_key_source_interval_window_and_filter_version(
    connection: Connection,
) -> None:
    source_id = factories.insert_source(connection)
    factories.insert_metric_bucket(connection, source_id=source_id, filter_version="f1")
    # Recomputing under a new filter definition adds a bucket rather than
    # rewriting the old one.
    factories.insert_metric_bucket(connection, source_id=source_id, filter_version="f2")

    with pytest.raises(IntegrityError):
        factories.insert_metric_bucket(connection, source_id=source_id, filter_version="f2")


def test_one_open_dispute_per_user_and_item(connection: Connection) -> None:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    prediction_id = factories.insert_prediction(connection, content_item_id=item_id)
    user_id = uuid4()

    _insert_dispute(connection, user_id=user_id, item_id=item_id, prediction_id=prediction_id)

    with pytest.raises(IntegrityError):
        _insert_dispute(connection, user_id=user_id, item_id=item_id, prediction_id=prediction_id)


def test_a_resolved_dispute_does_not_block_a_later_one(connection: Connection) -> None:
    """The rule is one *open* dispute. New evidence deserves a new dispute."""
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    prediction_id = factories.insert_prediction(connection, content_item_id=item_id)
    user_id = uuid4()

    first = _insert_dispute(
        connection, user_id=user_id, item_id=item_id, prediction_id=prediction_id
    )
    connection.execute(
        text(
            "UPDATE public.classification_disputes "
            "SET status = 'resolved_upheld', resolved_at = now() WHERE id = :id"
        ),
        {"id": first},
    )

    _insert_dispute(connection, user_id=user_id, item_id=item_id, prediction_id=prediction_id)


def test_a_published_resource_names_its_reviewer(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO public.resource_entries "
                "(title, organization, url, country_scope, category, summary, status) "
                "VALUES ('t', 'o', 'https://example.test/x', 'global', "
                "'understanding_islamophobia', 's', 'published')"
            )
        )


def test_a_resource_url_must_be_https(connection: Connection) -> None:
    with pytest.raises(IntegrityError):
        factories.insert_resource_entry(
            connection, url="http://example.test/insecure", status=PublicationStatus.draft
        )


def test_one_policy_version_per_platform_and_key(connection: Connection) -> None:
    _insert_policy(connection, version="1.0")
    _insert_policy(connection, version="1.1")

    with pytest.raises(IntegrityError):
        _insert_policy(connection, version="1.1")


def _insert_dispute(
    connection: Connection, *, user_id: UUID, item_id: UUID, prediction_id: UUID
) -> UUID:
    return UUID(
        str(
            connection.execute(
                text(
                    "INSERT INTO public.classification_disputes "
                    "(user_id, content_item_id, prediction_id, reason) "
                    "VALUES (:user_id, :item_id, :prediction_id, 'Synthetic reason') "
                    "RETURNING id"
                ),
                {"user_id": user_id, "item_id": item_id, "prediction_id": prediction_id},
            ).scalar_one()
        )
    )


def _insert_policy(connection: Connection, *, version: str) -> None:
    connection.execute(
        text(
            "INSERT INTO public.platform_policies "
            "(platform, policy_key, title, official_url, summary, version) "
            "VALUES ('youtube', 'hate_speech', 'Hate speech', "
            "'https://example.test/policy', 'Synthetic summary', :version)"
        ),
        {"version": version},
    )
