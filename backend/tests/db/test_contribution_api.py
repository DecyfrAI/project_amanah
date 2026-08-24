"""Submissions, disputes, and contribution history end to end (B-S16, B-S17).

These run the real application over the real schema. What they prove is the part
that cannot be proved in a unit test: the ownership boundary holds against a
second signed-in user, the state machine writes what it claims, and a retried
mutation converges instead of duplicating.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    Relevance,
    Severity,
    SourceKind,
    Stance,
    SubmissionStatus,
)
from amanah.main import create_app
from amanah.settings import Settings
from tests.conftest import make_access_token, make_settings
from tests.db import factories

SUBMISSIONS = "/v1/submissions"
CONTRIBUTIONS = "/v1/me/contributions"

OWNER = UUID("11111111-1111-1111-1111-111111111111")
STRANGER = UUID("22222222-2222-2222-2222-222222222222")

SUBMITTED_URL = "https://example.test/story-about-a-thing"


@pytest.fixture
def api_settings(database_url: str) -> Settings:
    return make_settings(database_url=database_url)


def _client_for(settings: Settings, user_id: UUID, role: str | None = None) -> TestClient:
    client = TestClient(create_app(settings))
    token = make_access_token(settings, user_id=user_id, role=role)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def owner(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, OWNER) as client:
        yield client


@pytest.fixture
def stranger(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, STRANGER) as client:
        yield client


@pytest.fixture
def submission_source(engine: Engine) -> UUID:
    """The configured source every user submission is attributed to."""
    with engine.begin() as connection:
        return factories.insert_source(
            connection,
            source_key="user_submission",
            kind=SourceKind.user_submission,
            platform=factories.PublicPlatform.user_submitted,
            name="User-submitted URLs",
        )


@pytest.fixture
def classified_item(engine: Engine) -> dict[str, Any]:
    """One item carrying a likely-anti-Muslim classification to dispute."""
    with engine.begin() as connection:
        source_id = factories.insert_source(connection, source_key="fixture_social")
        item_id = factories.insert_content_item(connection, source_id=source_id)
        prediction_id = factories.insert_prediction(
            connection,
            content_item_id=item_id,
            relevance=Relevance.muslim_related,
            stance=Stance.likely_anti_muslim,
            hate_types=(HateType.derogation.value,),
            severity=int(Severity.moderate),
            confidence_tier=ConfidenceTier.medium,
        )
    return {"item_id": item_id, "prediction_id": prediction_id}


# -- submissions ----------------------------------------------------------


def test_a_submission_is_recorded_as_processing_and_queues_a_run(
    owner: TestClient, submission_source: UUID, engine: Engine
) -> None:
    """FR-SUBMIT-005 and FR-SUBMIT-006: `processing` immediately, and the work
    goes onto the same queue collected content uses."""
    response = owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL})

    assert response.status_code == 201
    body = response.json()["submission"]
    assert body["status"] == SubmissionStatus.processing.value
    assert body["content_item_id"] is None

    with engine.connect() as connection:
        keys = connection.execute(
            text("SELECT idempotency_key FROM public.collection_runs")
        ).scalars()
        assert list(keys) == [f"submission:{body['id']}"]


def test_resubmitting_the_same_url_returns_the_existing_record(
    owner: TestClient, submission_source: UUID, engine: Engine
) -> None:
    """The natural key is `(user, canonical URL)`, so a retry converges rather
    than starting a second pipeline run."""
    first = owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL})
    second = owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL + "?utm_source=x"})

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["submission"]["id"] == first.json()["submission"]["id"]

    with engine.connect() as connection:
        runs = connection.execute(text("SELECT count(*) FROM public.collection_runs")).scalar_one()
        assert runs == 1


def test_a_url_matching_an_existing_item_is_recorded_as_a_duplicate(
    owner: TestClient, submission_source: UUID, engine: Engine
) -> None:
    """FR-SUBMIT-004: a canonical duplicate links to the item we already have
    instead of retrieving and classifying it a second time."""
    with engine.begin() as connection:
        source_id = factories.insert_source(connection, source_key="fixture_news_two")
        item_id = factories.insert_content_item(connection, source_id=source_id)
        connection.execute(
            text("UPDATE public.content_items SET canonical_url_key = :key WHERE id = :id"),
            {"key": "example.test/story-about-a-thing", "id": item_id},
        )

    response = owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL})

    body = response.json()["submission"]
    assert body["status"] == SubmissionStatus.duplicate.value
    assert body["content_item_id"] == str(item_id)
    with engine.connect() as connection:
        runs = connection.execute(text("SELECT count(*) FROM public.collection_runs")).scalar_one()
        assert runs == 0, "a duplicate must not queue retrieval"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/",  # an unsafe port, refused without a lookup
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://user:pass@example.test/",
    ],
)
def test_an_unsafe_destination_is_refused_before_anything_is_written(
    owner: TestClient, submission_source: UUID, engine: Engine, url: str
) -> None:
    """B-S11.2. Each of these is decidable without a resolver — a literal
    address, an unsafe port, credentials in the URL — so it is refused before a
    row exists to explain. A *name* that resolves privately is caught at
    retrieval instead; `tests/unit/test_safe_url_retrieval.py` covers that."""
    response = owner.post(SUBMISSIONS, json={"url": url})

    assert response.status_code == 422
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT count(*) FROM public.content_submissions")
        ).scalar_one()
        assert rows == 0


def test_a_submission_belongs_to_its_owner_alone(
    owner: TestClient, stranger: TestClient, submission_source: UUID
) -> None:
    created = owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL}).json()["submission"]

    assert owner.get(f"{SUBMISSIONS}/{created['id']}").status_code == 200
    assert stranger.get(f"{SUBMISSIONS}/{created['id']}").status_code == 404


def test_anonymous_callers_reach_no_contribution_route(
    api_settings: Settings, submission_source: UUID
) -> None:
    with TestClient(create_app(api_settings)) as client:
        assert client.post(SUBMISSIONS, json={"url": SUBMITTED_URL}).status_code == 401
        for path in (
            f"{SUBMISSIONS}/{uuid4()}",
            CONTRIBUTIONS,
            f"/v1/disputes/{uuid4()}",
        ):
            assert client.get(path).status_code == 401, path


def test_a_submission_appends_a_user_safe_timeline_line(
    owner: TestClient, submission_source: UUID
) -> None:
    """B-S16.4. The message is composed from controlled vocabulary, so no
    provider or source text can reach a timeline."""
    created = owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL}).json()["submission"]

    events = owner.get(f"{CONTRIBUTIONS}/{created['id']}/events").json()["events"]

    assert [event["event_type"] for event in events] == ["created"]
    assert events[0]["public_message"]


# -- disputes -------------------------------------------------------------


def test_a_dispute_creates_a_review_task_without_touching_the_prediction(
    owner: TestClient, classified_item: dict[str, Any], engine: Engine
) -> None:
    """FR-DISPUTE-004: the model's output is history, so a dispute adds a task
    and moves a projection rather than editing what the model said."""
    item_id = classified_item["item_id"]
    with engine.connect() as connection:
        before = connection.execute(
            text("SELECT stance FROM public.predictions WHERE id = :id"),
            {"id": classified_item["prediction_id"]},
        ).scalar_one()

    response = owner.post(
        f"/v1/items/{item_id}/disputes", json={"reason": "This reads as commentary to me."}
    )

    assert response.status_code == 201
    with engine.connect() as connection:
        after = connection.execute(
            text("SELECT stance FROM public.predictions WHERE id = :id"),
            {"id": classified_item["prediction_id"]},
        ).scalar_one()
        tasks = connection.execute(
            text("SELECT task_type, priority FROM public.review_tasks")
        ).all()
        state = connection.execute(
            text("SELECT effective_review_state FROM public.content_items WHERE id = :id"),
            {"id": item_id},
        ).scalar_one()

    assert after == before
    assert [(row.task_type, row.priority) for row in tasks] == [("dispute", 100)]
    assert state == "disputed"


def test_a_second_dispute_from_the_same_user_returns_the_open_one(
    owner: TestClient, classified_item: dict[str, Any], engine: Engine
) -> None:
    """`spec.md` section 14.6: one open dispute per user and item."""
    item_id = classified_item["item_id"]
    first = owner.post(f"/v1/items/{item_id}/disputes", json={"reason": "First reason."})
    second = owner.post(f"/v1/items/{item_id}/disputes", json={"reason": "Second reason."})

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["dispute"]["id"] == first.json()["dispute"]["id"]
    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM public.classification_disputes")
        ).scalar_one()
    assert count == 1


def test_two_users_disputing_one_item_share_a_single_review_task(
    owner: TestClient, stranger: TestClient, classified_item: dict[str, Any], engine: Engine
) -> None:
    """One question for a reviewer, not two: the queue must not multiply with the
    number of people who complained."""
    item_id = classified_item["item_id"]
    owner.post(f"/v1/items/{item_id}/disputes", json={"reason": "Owner reason."})
    stranger.post(f"/v1/items/{item_id}/disputes", json={"reason": "Stranger reason."})

    with engine.connect() as connection:
        tasks = connection.execute(text("SELECT count(*) FROM public.review_tasks")).scalar_one()
        disputes = connection.execute(
            text("SELECT count(*) FROM public.classification_disputes")
        ).scalar_one()

    assert tasks == 1
    assert disputes == 2


def test_an_unclassified_item_cannot_be_disputed(owner: TestClient, engine: Engine) -> None:
    with engine.begin() as connection:
        source_id = factories.insert_source(connection, source_key="fixture_unclassified")
        item_id = factories.insert_content_item(connection, source_id=source_id)

    response = owner.post(f"/v1/items/{item_id}/disputes", json={"reason": "No label here."})

    assert response.status_code == 422
    assert response.json()["error"]["details"]["safe_error_code"] == "item_has_no_classification"


def test_a_dispute_belongs_to_its_owner_alone(
    owner: TestClient, stranger: TestClient, classified_item: dict[str, Any]
) -> None:
    created = owner.post(
        f"/v1/items/{classified_item['item_id']}/disputes", json={"reason": "Mine."}
    ).json()["dispute"]

    assert owner.get(f"/v1/disputes/{created['id']}").status_code == 200
    assert stranger.get(f"/v1/disputes/{created['id']}").status_code == 404


# -- unified history ------------------------------------------------------


def test_the_history_gathers_every_contribution_type_newest_first(
    owner: TestClient, submission_source: UUID, classified_item: dict[str, Any]
) -> None:
    """`spec.md` section 9.10: one list across submissions, disputes, and
    prepared reports."""
    owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL})
    owner.post(f"/v1/items/{classified_item['item_id']}/disputes", json={"reason": "Mine."})

    page = owner.get(CONTRIBUTIONS).json()

    kinds = [row["contribution_type"] for row in page["items"]]
    assert sorted(kinds) == ["classification_dispute", "url_submission"]
    times = [row["created_at"] for row in page["items"]]
    assert times == sorted(times, reverse=True)


def test_the_history_can_be_narrowed_to_one_type(
    owner: TestClient, submission_source: UUID, classified_item: dict[str, Any]
) -> None:
    owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL})
    owner.post(f"/v1/items/{classified_item['item_id']}/disputes", json={"reason": "Mine."})

    page = owner.get(CONTRIBUTIONS, params={"contribution_type": "url_submission"}).json()

    assert [row["contribution_type"] for row in page["items"]] == ["url_submission"]


def test_an_unsupported_history_filter_is_a_client_error(owner: TestClient) -> None:
    response = owner.get(CONTRIBUTIONS, params={"platform": "youtube"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILTER"


def test_a_cursor_from_another_collection_is_refused(owner: TestClient) -> None:
    """A cursor carries the ordering it was issued for, so reusing one silently
    producing a page from the wrong ordering is not possible."""
    response = owner.get(CONTRIBUTIONS, params={"cursor": "bm90LWEtY3Vyc29y"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_the_history_never_shows_another_users_records(
    owner: TestClient, stranger: TestClient, submission_source: UUID
) -> None:
    owner.post(SUBMISSIONS, json={"url": SUBMITTED_URL})

    assert stranger.get(CONTRIBUTIONS).json()["items"] == []
