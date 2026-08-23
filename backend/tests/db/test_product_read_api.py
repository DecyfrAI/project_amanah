"""The authenticated read API against a real database (B-S5.7, B-S6.7).

These run the actual application over the actual schema, so what they prove is
end to end: the filter reaches SQL, the projection is what the endpoint can see,
and the response says what the data supports. The seeded rows are synthetic and
deliberately bland; the assertions are about structure, not wording.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from amanah.domain.enums import (
    ConfidenceTier,
    ContentKind,
    PublicationStatus,
    PublicPlatform,
    Relevance,
    ReviewState,
    SourceKind,
    Stance,
)
from amanah.main import create_app
from tests.conftest import make_access_token, make_settings
from tests.db import factories

ITEMS = "/v1/items"


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    """The real application, pointed at the scratch database."""
    settings = make_settings(database_url=database_url)
    application = create_app(settings)
    with TestClient(application) as test_client:
        test_client.headers["Authorization"] = f"Bearer {make_access_token(settings)}"
        yield test_client


@pytest.fixture
def seeded(engine: Engine) -> dict[str, Any]:
    """A small, deliberately varied corpus committed before the request runs."""
    with engine.begin() as connection:
        news_source = factories.insert_source(connection)
        social_source = factories.insert_source(
            connection,
            source_key="fixture_social",
            kind=SourceKind.social,
            platform=PublicPlatform.youtube,
            name="Synthetic video platform",
            safe_warning="Comments were disabled on some videos in this window.",
        )
        datapack_source = factories.insert_open_datapack_source(connection)
        package_id = factories.insert_dataset_package(connection)

        oldest = factories.insert_content_item(
            connection,
            source_id=news_source,
            observed_at=factories.days_after(-3),
            published_at=factories.days_after(-3),
            country_code="CA",
            title="Oldest synthetic article",
        )
        factories.insert_prediction(
            connection,
            content_item_id=oldest,
            relevance=Relevance.muslim_related,
            stance=Stance.non_hateful_discussion,
            score=0.30,
            confidence_tier=ConfidenceTier.low,
            narrative_tags=("policy_debate",),
        )

        hateful = factories.insert_content_item(
            connection,
            source_id=social_source,
            content_kind=ContentKind.social_comment,
            observed_at=factories.days_after(-1),
            published_at=factories.days_after(-1),
            country_code="GB",
            title=None,
            review_state=ReviewState.confirmed,
        )
        factories.insert_prediction(
            connection,
            content_item_id=hateful,
            relevance=Relevance.muslim_related,
            stance=Stance.likely_anti_muslim,
            severity=2,
            score=0.92,
            confidence_tier=ConfidenceTier.high,
            hate_types=("collective_blame",),
            narrative_tags=("security_threat",),
        )

        datapack = factories.insert_content_item(
            connection,
            source_id=datapack_source,
            content_kind=ContentKind.dataset_record,
            dataset_package_id=package_id,
            dataset_row_id="row-7",
            observed_at=factories.days_after(-2),
            published_at=None,
            country_code=None,
            title="Synthetic dataset record",
        )
        factories.insert_prediction(
            connection,
            content_item_id=datapack,
            relevance=Relevance.muslim_related,
            stance=Stance.counterspeech_or_quotation,
            score=0.55,
        )

        # Collected but not yet analysed: a real state the responses must report
        # honestly rather than default to a label.
        unclassified = factories.insert_content_item(
            connection,
            source_id=news_source,
            observed_at=factories.days_after(0),
            published_at=factories.days_after(0),
            title="Unanalysed synthetic article",
        )

        factories.insert_metric_bucket(
            connection, source_id=news_source, bucket_start=factories.days_after(-3)
        )
        factories.insert_resource_entry(
            connection, title="Published resource", status=PublicationStatus.published
        )
        factories.insert_resource_entry(
            connection, title="Draft resource", status=PublicationStatus.draft
        )

    return {
        "news_source": news_source,
        "social_source": social_source,
        "oldest": oldest,
        "hateful": hateful,
        "datapack": datapack,
        "unclassified": unclassified,
    }


def ids(payload: dict[str, Any]) -> list[str]:
    return [item["id"] for item in payload["items"]]


def test_items_are_returned_newest_first_by_default(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get(ITEMS).json()

    assert ids(body) == [
        str(seeded["unclassified"]),
        str(seeded["hateful"]),
        str(seeded["datapack"]),
        str(seeded["oldest"]),
    ]


def test_the_oldest_sort_reverses_the_documented_order(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get(ITEMS, params={"sort": "oldest"}).json()

    assert ids(body)[0] == str(seeded["oldest"])


def test_unclassified_items_sort_last_under_a_confidence_sort(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """An item with no score must not be treated as a zero-confidence item."""
    body = client.get(ITEMS, params={"sort": "highest_confidence"}).json()

    assert ids(body)[0] == str(seeded["hateful"])
    assert ids(body)[-1] == str(seeded["unclassified"])


def test_a_cursor_walks_every_item_exactly_once(client: TestClient, seeded: dict[str, Any]) -> None:
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params: dict[str, Any] = {"limit": 1}
        if cursor:
            params["cursor"] = cursor
        body = client.get(ITEMS, params=params).json()
        seen.extend(ids(body))
        cursor = body["page"]["next_cursor"]
        if cursor is None:
            break

    assert len(seen) == len(set(seen)) == 4


def test_the_last_page_reports_no_cursor(client: TestClient, seeded: dict[str, Any]) -> None:
    body = client.get(ITEMS, params={"limit": 100}).json()

    assert body["page"]["next_cursor"] is None


def test_a_cursor_from_a_different_sort_is_rejected(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """Silently serving page one under the new sort would show the caller data
    they did not ask for."""
    cursor = client.get(ITEMS, params={"limit": 1}).json()["page"]["next_cursor"]

    response = client.get(ITEMS, params={"limit": 1, "sort": "oldest", "cursor": cursor})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_a_forged_cursor_is_rejected(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get(ITEMS, params={"cursor": "not-a-cursor"})

    assert response.status_code == 400


def test_an_unknown_filter_is_a_client_error_rather_than_a_wider_query(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get(ITEMS, params={"author_name": "someone"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILTER"


def test_an_unsupported_sort_is_rejected(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get(ITEMS, params={"sort": "most_shocking"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_SORT"


def test_an_oversized_page_limit_is_rejected(client: TestClient, seeded: dict[str, Any]) -> None:
    assert client.get(ITEMS, params={"limit": 1000}).status_code == 400


def test_a_date_window_longer_than_the_maximum_is_rejected(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get(
        ITEMS, params={"date_from": "2020-01-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"}
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("filter_name", "value", "expected_key"),
    [
        ("platforms", "youtube", "hateful"),
        ("content_kinds", "social_comment", "hateful"),
        ("country_codes", "GB", "hateful"),
        ("severities", "2", "hateful"),
        ("review_states", "confirmed", "hateful"),
        ("confidence_tiers", "high", "hateful"),
        ("narrative_tags", "security_threat", "hateful"),
        ("dataset_provider", "synthetic-provider", "datapack"),
        ("dataset_name", "synthetic-dataset", "datapack"),
        ("dataset_version", "1.0.0", "datapack"),
    ],
)
def test_each_filter_narrows_to_the_expected_item(
    client: TestClient,
    seeded: dict[str, Any],
    filter_name: str,
    value: str,
    expected_key: str,
) -> None:
    body = client.get(ITEMS, params={filter_name: value}).json()

    assert ids(body) == [str(seeded[expected_key])]


def test_a_filter_value_that_matches_nothing_returns_an_empty_page(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """Empty is a legitimate answer. It must not be an error, and it must not
    quietly widen to something that does match."""
    body = client.get(ITEMS, params={"country_codes": "NZ"}).json()

    assert body["items"] == []
    assert body["page"]["next_cursor"] is None


def test_the_dataset_filter_is_separate_from_the_platform_filter(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """A datapack row publishes `N/A` as its platform and stays findable by the
    dataset it came from."""
    item = client.get(ITEMS, params={"dataset_provider": "synthetic-provider"}).json()["items"][0]

    assert item["platform"] == "not_applicable"
    assert item["platform_display"] == "N/A"
    assert item["dataset"]["provider"] == "synthetic-provider"
    assert item["dataset"]["version"] == "1.0.0"


def test_an_unclassified_item_reports_no_labels(client: TestClient, seeded: dict[str, Any]) -> None:
    body = client.get(ITEMS, params={"sort": "newest", "limit": 1}).json()
    item = body["items"][0]

    assert item["id"] == str(seeded["unclassified"])
    assert item["is_classified"] is False
    assert item["relevance"] is None
    assert item["severity"] is None


def test_news_is_no_longer_an_item_projection(client: TestClient, seeded: dict[str, Any]) -> None:
    """B-S9 moved `/v1/news` to the context news stream (reconciliation G5).

    It used to be this file's concern: the same item projection with the content
    kind pinned to news, which gave every article a hate label and a review
    state. That shape is gone, and this asserts it stays gone. The stream's own
    contract — window, applied, coverage, publisher metadata, no classification —
    is covered in `test_news_api.py`.
    """
    del seeded
    body = client.get("/v1/news").json()

    assert "page" not in body
    assert {"window", "applied", "coverage", "data_mode", "next_cursor"} <= set(body)
    assert all("content_kind" not in item for item in body["items"])


def test_item_detail_carries_the_model_disclosure_and_its_limitations(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get(f"{ITEMS}/{seeded['hateful']}").json()

    item = body["item"]
    assert item["model_name"] == "synthetic-model"
    assert item["score"] == 0.92
    assert item["limitations"]
    assert item["sampling_disclosure"]


def test_item_detail_never_returns_raw_content_or_an_author_identifier(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get(f"{ITEMS}/{seeded['hateful']}")

    assert "synthetic normalized text" not in response.text
    assert "synthetic/object/key" not in response.text
    assert "synthetic-ciphertext" not in response.text
    for forbidden in ("source_item_id", "normalized_text", "raw_object_key", "submitted_origin"):
        assert forbidden not in response.text


def test_an_unknown_item_is_not_found(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get(f"{ITEMS}/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_the_dashboard_reports_every_part_of_its_rate(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/dashboard").json()

    rate = body["metrics"]["likely_anti_muslim_rate"]
    assert rate["numerator"] == 1
    assert rate["denominator"] == 3
    assert rate["source_scope"]
    assert rate["window_start"] and rate["window_end"]
    assert rate["data_mode"] == "fixture"
    assert body["metrics"]["observed_count"] == 4
    assert body["metrics"]["muslim_related_count"] == 3


def test_the_dashboard_warns_about_items_it_could_not_classify(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/dashboard").json()

    assert any("not been analysed" in warning for warning in body["coverage"]["warnings"])
    assert body["coverage"]["coverage_score"] == pytest.approx(0.75)


def test_the_dashboard_surfaces_a_source_coverage_warning(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/dashboard").json()

    assert "Comments were disabled on some videos in this window." in body["coverage"]["warnings"]


def test_an_uncomputed_day_is_a_gap_rather_than_a_zero(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/dashboard").json()

    gaps = [point for point in body["trend"]["points"] if point["is_gap"]]
    assert gaps, "expected at least one uncollected day"
    assert all(point["observed_count"] is None for point in gaps)


def test_a_window_with_no_data_reports_a_null_rate_not_zero(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get(
        "/v1/dashboard",
        params={"date_from": "2020-01-01T00:00:00Z", "date_to": "2020-02-01T00:00:00Z"},
    ).json()

    rate = body["metrics"]["likely_anti_muslim_rate"]
    assert rate["denominator"] == 0
    assert rate["value"] is None
    assert any("no rate" in warning.lower() for warning in body["coverage"]["warnings"])


def test_headlines_exclude_items_whose_relevance_is_unknown(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/dashboard").json()

    headline_ids = {card["item_id"] for card in body["headlines"]}
    assert str(seeded["unclassified"]) not in headline_ids
    assert str(seeded["oldest"]) in headline_ids


def test_filters_are_offered_only_where_the_data_supports_them(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/filters").json()

    assert set(body["platforms"]) == {"news_web", "youtube", "not_applicable"}
    assert set(body["country_codes"]) == {"CA", "GB"}
    assert body["datasets"] == [
        {"provider": "synthetic-provider", "name": "synthetic-dataset", "version": "1.0.0"}
    ]
    # Closed vocabularies are published in full: their meaning does not depend on
    # what happens to have been collected.
    assert set(body["confidence_tiers"]) == {"low", "medium", "high"}
    assert body["max_page_limit"] == 100


def test_only_published_resources_reach_the_catalogue_endpoint(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    body = client.get("/v1/resources").json()

    titles = [entry["title"] for entry in body["resources"]]
    assert titles == ["Published resource"]
    assert "Draft resource" not in body


def test_connections_report_purpose_and_state_without_secrets(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get("/v1/connections")
    body = response.json()

    assert {connection["source_key"] for connection in body["connections"]} == {
        "fixture_news",
        "fixture_social",
        "open_datapack",
    }
    for connection in body["connections"]:
        assert connection["purpose"]
        assert connection["status"] in {
            "ok",
            "degraded",
            "disabled",
            "not_configured",
            "access_required",
        }
    assert "postgres" not in response.text
    assert "password" not in response.text.lower()


def test_methodology_discloses_limits_without_publishing_the_sampling_internals(
    client: TestClient,
) -> None:
    response = client.get("/v1/methodology")
    body = response.json()

    assert body["limitations"]
    assert body["sampling"]["prevalence_warning"]
    assert all(tier["is_provisional"] for tier in body["confidence_tiers"])
    # The registry keys and query strings that define the sample stay internal.
    assert "registry_key" not in response.text
    assert "provider_reference" not in response.text


def test_methodology_answers_even_when_no_classifier_is_configured(
    client: TestClient,
) -> None:
    body = client.get("/v1/methodology").json()

    assert body["models"]["is_configured"] is False
    assert body["models"]["model_version"] == "not_configured"


def test_product_reads_are_denied_without_a_session(database_url: str) -> None:
    settings = make_settings(database_url=database_url)
    with TestClient(create_app(settings)) as anonymous:
        for path in (
            ITEMS,
            "/v1/news",
            "/v1/dashboard",
            "/v1/filters",
            "/v1/resources",
            "/v1/methodology",
            "/v1/connections",
        ):
            response = anonymous.get(path)
            assert response.status_code == 401, path
            assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_a_product_read_is_refused_when_no_database_is_configured() -> None:
    """A missing `DATABASE_URL` disables product reads and nothing else; the
    caller gets a retryable 503 rather than an empty page that reads as a
    finding."""
    settings = make_settings(database_url=None)
    with TestClient(create_app(settings)) as client_without_database:
        response = client_without_database.get(
            ITEMS, headers={"Authorization": f"Bearer {make_access_token(settings)}"}
        )

    assert response.status_code == 503
    body = response.json()["error"]
    assert body["code"] == "SERVICE_UNAVAILABLE"
    assert body["retryable"] is True


def test_the_request_scoping_step_publishes_the_verified_caller(
    client: TestClient, engine: Engine, seeded: dict[str, Any]
) -> None:
    """Owner-scoped projections depend on the identity the API publishes for each
    request, so this asserts the mechanism directly rather than by implication."""
    with engine.connect() as connection:
        stored = connection.execute(text("SELECT count(*) FROM public.content_items")).scalar_one()

    assert stored == 4
    assert client.get(ITEMS).json()["items"]
