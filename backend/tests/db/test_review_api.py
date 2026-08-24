"""The reviewer queue, claims, and append-only decisions (B-S17.4 to B-S17.8).

The properties worth proving here are the ones a single-threaded happy path
hides: a second reviewer cannot take a claimed task, a decision cannot be
appended without holding the claim, a prediction is never rewritten, and an
approved correction lands in a quarantine nothing consumes.
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
    Stance,
)
from amanah.main import create_app
from amanah.settings import Settings
from tests.conftest import make_access_token, make_settings
from tests.db import factories

TASKS = "/v1/review/tasks"

DISPUTER = UUID("33333333-3333-3333-3333-333333333333")
FIRST_REVIEWER = UUID("44444444-4444-4444-4444-444444444444")
SECOND_REVIEWER = UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture
def api_settings(database_url: str) -> Settings:
    return make_settings(database_url=database_url)


def _client_for(settings: Settings, user_id: UUID, role: str | None = None) -> TestClient:
    client = TestClient(create_app(settings))
    token = make_access_token(settings, user_id=user_id, role=role)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def disputer(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, DISPUTER) as client:
        yield client


@pytest.fixture
def reviewer(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, FIRST_REVIEWER, role="reviewer") as client:
        yield client


@pytest.fixture
def other_reviewer(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, SECOND_REVIEWER, role="reviewer") as client:
        yield client


@pytest.fixture
def disputed(engine: Engine, disputer: TestClient) -> dict[str, Any]:
    """One item with a likely-hate classification and an open dispute on it."""
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
    dispute = disputer.post(
        f"/v1/items/{item_id}/disputes", json={"reason": "I read this as commentary."}
    ).json()["dispute"]
    return {"item_id": item_id, "prediction_id": prediction_id, "dispute_id": dispute["id"]}


def _task_id(reviewer: TestClient) -> str:
    page = reviewer.get(TASKS).json()
    assert page["items"], "the dispute should have queued a task"
    task_id: str = page["items"][0]["id"]
    return task_id


# -- authorization --------------------------------------------------------


def test_a_base_role_user_cannot_reach_the_queue(
    disputer: TestClient, disputed: dict[str, Any]
) -> None:
    assert disputer.get(TASKS).status_code == 403


def test_an_anonymous_caller_cannot_reach_the_queue(api_settings: Settings) -> None:
    with TestClient(create_app(api_settings)) as client:
        assert client.get(TASKS).status_code == 401


def test_the_queue_never_names_the_person_who_disputed(
    reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    """A decision is about the model's output. Knowing who complained could only
    bias it, so the projection has no column for them."""
    entry = reviewer.get(TASKS).json()["items"][0]

    assert str(DISPUTER) not in str(entry)
    assert "user_id" not in entry


# -- claims ---------------------------------------------------------------


def test_a_second_reviewer_cannot_take_a_claimed_task(
    reviewer: TestClient, other_reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    task_id = _task_id(reviewer)

    first = reviewer.post(f"{TASKS}/{task_id}/claim")
    second = other_reviewer.post(f"{TASKS}/{task_id}/claim")

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "RESOURCE_CONFLICT"


def test_reclaiming_your_own_task_renews_it_rather_than_failing(
    reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    """A reviewer whose page reloaded should not lose their place."""
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")

    assert reviewer.post(f"{TASKS}/{task_id}/claim").status_code == 200


def test_a_decision_without_a_claim_is_refused(
    reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    task_id = _task_id(reviewer)

    response = reviewer.post(f"{TASKS}/{task_id}/decisions", json={"decision": "confirmed"})

    assert response.status_code == 409


def test_a_reviewer_cannot_decide_on_another_reviewers_claim(
    reviewer: TestClient, other_reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")

    response = other_reviewer.post(f"{TASKS}/{task_id}/decisions", json={"decision": "confirmed"})

    assert response.status_code == 409


# -- decisions ------------------------------------------------------------


def test_a_confirmation_leaves_the_prediction_untouched(
    reviewer: TestClient, disputed: dict[str, Any], engine: Engine
) -> None:
    """FR-DISPUTE-004: review events append; they do not overwrite the model."""
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")
    with engine.connect() as connection:
        before = connection.execute(
            text("SELECT stance, score FROM public.predictions WHERE id = :id"),
            {"id": disputed["prediction_id"]},
        ).one()

    reviewer.post(f"{TASKS}/{task_id}/decisions", json={"decision": "confirmed"})

    with engine.connect() as connection:
        after = connection.execute(
            text("SELECT stance, score FROM public.predictions WHERE id = :id"),
            {"id": disputed["prediction_id"]},
        ).one()
        state = connection.execute(
            text("SELECT effective_review_state FROM public.content_items WHERE id = :id"),
            {"id": disputed["item_id"]},
        ).scalar_one()

    assert after == before
    assert state == "confirmed"


def test_a_correction_updates_the_effective_label_and_resolves_the_dispute(
    reviewer: TestClient, disputer: TestClient, disputed: dict[str, Any], engine: Engine
) -> None:
    """B-S17.5 and B-S17.6: the projection moves and the user is told, in words
    composed here rather than copied from the reviewer's note."""
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")

    reviewer.post(
        f"{TASKS}/{task_id}/decisions",
        json={
            "decision": "corrected",
            "corrected_labels": {"stance": "non_hateful_discussion"},
            "note": "Internal reviewer note that must not be published.",
            "is_training_candidate": True,
        },
    )

    dispute = disputer.get(f"/v1/disputes/{disputed['dispute_id']}").json()["dispute"]
    assert dispute["status"] == "resolved_corrected"
    assert dispute["resolution_summary"]
    assert "Internal reviewer note" not in dispute["resolution_summary"]
    assert dispute["resolved_at"] is not None

    with engine.connect() as connection:
        state = connection.execute(
            text("SELECT effective_review_state FROM public.content_items WHERE id = :id"),
            {"id": disputed["item_id"]},
        ).scalar_one()
    assert state == "corrected"


def test_the_reviewers_private_note_never_reaches_the_users_timeline(
    reviewer: TestClient, disputer: TestClient, disputed: dict[str, Any]
) -> None:
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")
    reviewer.post(
        f"{TASKS}/{task_id}/decisions",
        json={"decision": "confirmed", "note": "SECRET-REVIEWER-REASONING"},
    )

    events = disputer.get(f"/v1/me/contributions/{disputed['dispute_id']}/events").json()["events"]

    assert [event["event_type"] for event in events] == ["created", "resolved"]
    assert "SECRET-REVIEWER-REASONING" not in str(events)


def test_an_approved_correction_is_quarantined_and_nothing_consumes_it(
    reviewer: TestClient, disputed: dict[str, Any], engine: Engine
) -> None:
    """`spec.md` section 15.3: a correction enters a governed pool. The flag has
    no consumer anywhere in this service, and that absence is the quarantine."""
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")
    reviewer.post(
        f"{TASKS}/{task_id}/decisions",
        json={
            "decision": "corrected",
            "corrected_labels": {"stance": "non_hateful_discussion"},
            "is_training_candidate": True,
        },
    )

    with engine.connect() as connection:
        flagged = connection.execute(
            text("SELECT count(*) FROM public.review_events WHERE is_training_candidate")
        ).scalar_one()
    assert flagged == 1


def test_a_decision_is_appended_rather_than_replacing_an_earlier_one(
    reviewer: TestClient, other_reviewer: TestClient, disputed: dict[str, Any], engine: Engine
) -> None:
    """Two reviewers who disagreed must both stay in the record."""
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")
    reviewer.post(f"{TASKS}/{task_id}/decisions", json={"decision": "confirmed"})

    # The task completed, so a second reviewer has to reopen it by claiming; the
    # claim is refused, which is the state machine working. Append directly to
    # prove the history table itself refuses an overwrite rather than a second row.
    with engine.begin() as connection:
        event_id = connection.execute(
            text("SELECT id FROM public.review_events LIMIT 1")
        ).scalar_one()
        with pytest.raises(Exception, match="append_only_violation"):
            connection.execute(
                text("UPDATE public.review_events SET decision = 'rejected' WHERE id = :id"),
                {"id": event_id},
            )


def test_a_completed_task_cannot_be_claimed_again(
    reviewer: TestClient, other_reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")
    reviewer.post(f"{TASKS}/{task_id}/decisions", json={"decision": "confirmed"})

    assert other_reviewer.post(f"{TASKS}/{task_id}/claim").status_code == 409


def test_the_decision_history_is_readable_on_the_task(
    reviewer: TestClient, disputed: dict[str, Any]
) -> None:
    task_id = _task_id(reviewer)
    reviewer.post(f"{TASKS}/{task_id}/claim")
    reviewer.post(f"{TASKS}/{task_id}/decisions", json={"decision": "needs_context"})

    task = reviewer.get(f"{TASKS}/{task_id}").json()

    assert [entry["decision"] for entry in task["decisions"]] == ["needs_context"]
    assert task["task"]["status"] == "completed"


def test_an_unknown_task_is_not_found(reviewer: TestClient) -> None:
    assert reviewer.get(f"{TASKS}/{uuid4()}").status_code == 404
