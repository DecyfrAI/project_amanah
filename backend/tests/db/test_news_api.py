"""`GET /v1/news` as the context news stream (B-S9.8, reconciliation G5).

The contract question and the safety question are the same one here: an
ingested article must not arrive shaped like a finding. So these check the agreed
field names *and* that no classification field can appear, including for an
article that happens to have a prediction attached to it in the database.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from amanah.domain.enums import (
    ConfidenceTier,
    ContentKind,
    NewsScope,
    PublicPlatform,
    Relevance,
    Role,
    SourceKind,
    Stance,
)
from amanah.main import create_app
from tests.conftest import make_access_token, make_settings
from tests.db import factories

NEWS = "/v1/news"

#: Nothing in a news response may be shaped like a finding.
FORBIDDEN_FIELDS = frozenset(
    {
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
)


@pytest.fixture
def application(database_url: str) -> Any:
    return create_app(make_settings(database_url=database_url))


@pytest.fixture
def client(application: Any) -> Iterator[TestClient]:
    settings = application.state.settings
    with TestClient(application) as test_client:
        token = make_access_token(settings, role=Role.registered_user)
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client


@pytest.fixture
def anonymous(application: Any) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def seeded(engine: Engine) -> dict[str, Any]:
    """Three articles and one social comment, plus a prediction on one article."""
    with engine.begin() as connection:
        news_source = factories.insert_source(
            connection,
            source_key="rss_synthetic",
            kind=SourceKind.news,
            name="Synthetic Wire",
        )
        connection.execute(
            text("UPDATE public.sources SET homepage_url = :url WHERE id = :id"),
            {"url": "https://example.test", "id": news_source},
        )
        social_source = factories.insert_source(
            connection,
            source_key="fixture_social",
            kind=SourceKind.social,
            platform=PublicPlatform.youtube,
            name="Synthetic video platform",
        )

        oldest = factories.insert_content_item(
            connection,
            source_id=news_source,
            source_item_id="news-oldest",
            content_kind=ContentKind.news_article,
            title="Council debates funding",
            observed_at=factories.days_after(-10),
            published_at=factories.days_after(-10),
        )
        newest = factories.insert_content_item(
            connection,
            source_id=news_source,
            source_item_id="news-newest",
            content_kind=ContentKind.news_article,
            title="Police publish hate crime figures",
            observed_at=factories.days_after(-1),
            published_at=factories.days_after(-1),
        )
        # An article that *does* carry a prediction. The news stream must still
        # not publish it.
        factories.insert_prediction(
            connection,
            content_item_id=newest,
            relevance=Relevance.muslim_related,
            stance=Stance.non_hateful_discussion,
            score=0.4,
            confidence_tier=ConfidenceTier.medium,
        )
        factories.insert_content_item(
            connection,
            source_id=social_source,
            source_item_id="comment-1",
            content_kind=ContentKind.social_comment,
            title=None,
            observed_at=factories.days_after(-2),
            published_at=factories.days_after(-2),
        )
    return {"oldest": oldest, "newest": newest}


def _window() -> dict[str, str]:
    return {
        "from": factories.days_after(-30).date().isoformat(),
        "to": factories.days_after(1).date().isoformat(),
    }


def test_an_anonymous_caller_gets_no_news(anonymous: TestClient) -> None:
    assert anonymous.get(NEWS).status_code == 401


def test_the_response_carries_the_agreed_envelope(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    del seeded
    body = client.get(NEWS, params=_window()).json()

    assert set(body) >= {"window", "applied", "coverage", "data_mode", "next_cursor", "items"}
    assert set(body["window"]) == {"from", "to", "timezone"}
    assert set(body["applied"]) == {"from", "to"}
    assert set(body["coverage"]) == {
        "sources",
        "items_retrieved",
        "last_successful_run",
        "warnings",
    }


def test_only_news_articles_appear(client: TestClient, seeded: dict[str, Any]) -> None:
    """A social comment is an item, not a headline."""
    del seeded
    body = client.get(NEWS, params=_window()).json()

    assert len(body["items"]) == 2
    titles = {item["title"] for item in body["items"]}
    assert titles == {"Council debates funding", "Police publish hate crime figures"}


def test_no_item_carries_a_classification(client: TestClient, seeded: dict[str, Any]) -> None:
    """The heart of G5. One of these articles has a prediction in the database."""
    del seeded
    body = client.get(NEWS, params=_window()).json()

    for item in body["items"]:
        assert FORBIDDEN_FIELDS.isdisjoint(set(item))


def test_an_item_carries_publisher_metadata_only(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    del seeded
    item = client.get(NEWS, params=_window()).json()["items"][0]

    assert set(item) == {
        "id",
        "source_name",
        "source_homepage",
        "title",
        "summary",
        "url",
        "published_at",
        "retrieved_at",
        "language",
        "scope",
        "location",
    }
    assert item["source_name"] == "Synthetic Wire"
    assert item["source_homepage"] == "https://example.test"
    assert item["scope"] in {NewsScope.local.value, NewsScope.globally.value}


def test_articles_are_returned_newest_first(client: TestClient, seeded: dict[str, Any]) -> None:
    del seeded
    body = client.get(NEWS, params=_window()).json()

    assert body["items"][0]["title"] == "Police publish hate crime figures"


def test_the_window_is_applied(client: TestClient, seeded: dict[str, Any]) -> None:
    del seeded
    narrow = {
        "from": factories.days_after(-3).date().isoformat(),
        "to": factories.days_after(1).date().isoformat(),
    }

    body = client.get(NEWS, params=narrow).json()

    assert len(body["items"]) == 1
    assert body["applied"]["from"] == narrow["from"]


def test_an_empty_window_is_a_gap_with_coverage_rather_than_a_bare_zero(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """`rules/backend.md`: never represent missing data as zero. The coverage
    block is what lets a reader tell "nothing happened" from "nothing ran"."""
    del seeded
    body = client.get(
        NEWS,
        params={
            "from": factories.days_after(-400).date().isoformat(),
            "to": factories.days_after(-390).date().isoformat(),
        },
    ).json()

    assert body["items"] == []
    assert body["coverage"]["items_retrieved"] == 0
    assert "last_successful_run" in body["coverage"]


def test_coverage_names_the_publishers_in_the_window(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    del seeded
    body = client.get(NEWS, params=_window()).json()

    assert body["coverage"]["sources"] == ["Synthetic Wire"]
    assert body["coverage"]["items_retrieved"] == 2


def test_the_stream_pages_with_a_cursor(client: TestClient, seeded: dict[str, Any]) -> None:
    del seeded
    first = client.get(NEWS, params={**_window(), "limit": 1}).json()

    assert len(first["items"]) == 1
    assert first["next_cursor"] is not None

    second = client.get(
        NEWS, params={**_window(), "limit": 1, "cursor": first["next_cursor"]}
    ).json()

    assert len(second["items"]) == 1
    assert second["items"][0]["id"] != first["items"][0]["id"]
    assert second["next_cursor"] is None


def test_a_malformed_cursor_is_a_client_error(client: TestClient, seeded: dict[str, Any]) -> None:
    del seeded
    assert client.get(NEWS, params={"cursor": "not-a-cursor"}).status_code == 400


def test_a_reversed_window_is_refused(client: TestClient) -> None:
    response = client.get(NEWS, params={"from": "2026-08-01", "to": "2026-07-01"})

    assert response.status_code == 400
    assert response.json()["error"]["details"]["fields"] == ["from"]


def test_an_unbounded_window_is_refused(client: TestClient) -> None:
    response = client.get(NEWS, params={"from": "2000-01-01", "to": "2026-08-01"})

    assert response.status_code == 400


def test_a_classification_filter_is_not_silently_broadened(client: TestClient) -> None:
    """`rules/api.md`: an unsupported filter is a client error, never a query the
    server quietly widens. `severity` means nothing for an unclassified article."""
    response = client.get(NEWS, params={**_window(), "severity": "3"})

    assert response.status_code == 400


def test_the_default_window_is_applied_when_none_is_given(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    del seeded
    body = client.get(NEWS).json()

    assert body["window"]["timezone"] == "UTC"
    assert body["applied"]["from"] < body["applied"]["to"]
