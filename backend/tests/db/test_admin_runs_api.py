"""`/v1/admin/runs` against a real database (B-S7.6, B-S7.7).

Two questions are asked here. Does an operator get the run state they need, and
does anyone else get nothing at all? The second is checked at both layers: the
route dependency and the administrator predicate carried by the projection.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from amanah.domain.enums import CollectionMode, JobStage, JobState, Role
from amanah.jobs.service import JobService
from amanah.main import create_app
from tests.conftest import make_access_token, make_settings
from tests.db import factories

RUNS = "/v1/admin/runs"
SOURCE_KEY = "fixture_news"


@pytest.fixture
def application(database_url: str) -> Any:
    return create_app(make_settings(database_url=database_url))


def _client(application: Any, role: Role | None) -> Iterator[TestClient]:
    settings = application.state.settings
    with TestClient(application) as test_client:
        if role is not None:
            token = make_access_token(settings, role=role)
            test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client


@pytest.fixture
def administrator(application: Any) -> Iterator[TestClient]:
    yield from _client(application, Role.administrator)


@pytest.fixture
def base_user(application: Any) -> Iterator[TestClient]:
    yield from _client(application, Role.registered_user)


@pytest.fixture
def anonymous(application: Any) -> Iterator[TestClient]:
    yield from _client(application, None)


@pytest.fixture
def source(engine: Engine) -> None:
    with engine.begin() as connection:
        factories.insert_source(connection, source_key=SOURCE_KEY)


def _dispatch_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "source_key": SOURCE_KEY,
        "mode": CollectionMode.fixture.value,
        "idempotency_key": f"manual-{uuid4().hex}",
    }
    body.update(overrides)
    return body


def test_an_anonymous_caller_reads_no_run_state(anonymous: TestClient) -> None:
    assert anonymous.get(RUNS).status_code == 401


def test_a_base_role_user_is_denied(base_user: TestClient) -> None:
    assert base_user.get(RUNS).status_code == 403


def test_an_administrator_dispatches_a_bounded_run(administrator: TestClient, source: None) -> None:
    del source
    response = administrator.post(RUNS, json=_dispatch_body(item_cap=25))

    assert response.status_code == 201
    run = response.json()["run"]
    assert run["source_key"] == SOURCE_KEY
    assert run["item_cap"] == 25
    assert run["status"] == JobState.queued.value
    assert run["is_dead_lettered"] is False


def test_redelivering_a_dispatch_returns_the_existing_run(
    administrator: TestClient, source: None
) -> None:
    """A retried dispatch must not double-collect against a live provider."""
    del source
    body = _dispatch_body()

    created = administrator.post(RUNS, json=body)
    repeated = administrator.post(RUNS, json=body)

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["run"]["id"] == created.json()["run"]["id"]


def test_a_cap_above_the_ceiling_is_refused(administrator: TestClient, source: None) -> None:
    del source
    response = administrator.post(RUNS, json=_dispatch_body(item_cap=1_000_000))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_a_reversed_window_is_refused(administrator: TestClient, source: None) -> None:
    del source
    response = administrator.post(
        RUNS,
        json=_dispatch_body(
            window_start="2026-06-30T00:00:00+00:00",
            window_end="2026-06-01T00:00:00+00:00",
        ),
    )

    assert response.status_code == 400


def test_an_unknown_source_key_names_the_field_to_fix(
    administrator: TestClient, source: None
) -> None:
    del source
    response = administrator.post(RUNS, json=_dispatch_body(source_key="never-configured"))

    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"] == ["source_key"]


def test_a_scheduled_run_cannot_be_dispatched_by_hand(
    administrator: TestClient, source: None
) -> None:
    """Letting a person claim `scheduled` would make run provenance a lie."""
    del source
    response = administrator.post(RUNS, json=_dispatch_body(mode=CollectionMode.scheduled.value))

    assert response.status_code == 400


def test_the_run_list_pages_with_a_cursor(administrator: TestClient, source: None) -> None:
    del source
    for _ in range(3):
        administrator.post(RUNS, json=_dispatch_body())

    first = administrator.get(RUNS, params={"limit": 2}).json()
    assert len(first["items"]) == 2
    assert first["page"]["next_cursor"] is not None

    second = administrator.get(
        RUNS, params={"limit": 2, "cursor": first["page"]["next_cursor"]}
    ).json()

    assert len(second["items"]) == 1
    assert second["page"]["next_cursor"] is None
    seen = {item["id"] for item in first["items"]} | {item["id"] for item in second["items"]}
    assert len(seen) == 3


def test_a_malformed_cursor_is_a_client_error_not_page_one(
    administrator: TestClient, source: None
) -> None:
    del source
    administrator.post(RUNS, json=_dispatch_body())

    response = administrator.get(RUNS, params={"cursor": "not-a-cursor"})

    assert response.status_code == 400


def test_the_run_list_filters_by_status(administrator: TestClient, source: None) -> None:
    del source
    administrator.post(RUNS, json=_dispatch_body())

    matching = administrator.get(RUNS, params={"status": JobState.queued.value}).json()
    other = administrator.get(RUNS, params={"status": JobState.succeeded.value}).json()

    assert len(matching["items"]) == 1
    assert other["items"] == []


def test_an_unsupported_status_is_rejected(administrator: TestClient, source: None) -> None:
    del source
    assert administrator.get(RUNS, params={"status": "not-a-state"}).status_code == 400


def test_run_detail_lists_the_stages_beneath_it(
    administrator: TestClient, source: None, engine: Engine
) -> None:
    del source
    created = administrator.post(RUNS, json=_dispatch_body()).json()["run"]
    from sqlalchemy.orm import sessionmaker

    with sessionmaker(bind=engine, expire_on_commit=False)() as active:
        JobService(active).enqueue(
            collection_run_id=created["id"],
            stage=JobStage.discover,
            idempotency_key=f"{created['id']}:discover",
        )

    response = administrator.get(f"{RUNS}/{created['id']}")

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert [job["stage"] for job in jobs] == [JobStage.discover.value]
    assert jobs[0]["state"] == JobState.queued.value


def test_run_detail_never_publishes_the_queue_message_or_its_holder(
    administrator: TestClient, source: None, engine: Engine
) -> None:
    """A checkpoint can hold a provider cursor and a lease owner names a worker."""
    del source
    created = administrator.post(RUNS, json=_dispatch_body()).json()["run"]
    from sqlalchemy.orm import sessionmaker

    with sessionmaker(bind=engine, expire_on_commit=False)() as active:
        service = JobService(active)
        service.enqueue(
            collection_run_id=created["id"],
            stage=JobStage.discover,
            idempotency_key=f"{created['id']}:discover",
            payload={"secret_cursor": "provider-token"},
        )
        service.claim_next(worker_id="worker-a")

    body = administrator.get(f"{RUNS}/{created['id']}").text

    assert "provider-token" not in body
    assert "worker-a" not in body


def test_an_unknown_run_is_not_found(administrator: TestClient) -> None:
    assert administrator.get(f"{RUNS}/{uuid4()}").status_code == 404


def test_a_base_role_user_cannot_read_one_run(base_user: TestClient, engine: Engine) -> None:
    """Denied by the dependency, and the projection would return nothing anyway."""
    with engine.begin() as connection:
        source_id = factories.insert_source(connection, source_key=SOURCE_KEY)
        run_id = factories.insert_collection_run(connection, source_id=source_id)

    assert base_user.get(f"{RUNS}/{run_id}").status_code == 403


def test_the_projection_alone_hides_runs_from_a_non_administrator(
    engine: Engine,
) -> None:
    """The route dependency is one boundary; this is the other. Even reading the
    view directly as a base-role caller returns nothing."""
    with engine.begin() as connection:
        source_id = factories.insert_source(connection, source_key=SOURCE_KEY)
        factories.insert_collection_run(connection, source_id=source_id)

    from tests.db.conftest import act_as, claims_for

    with engine.connect() as connection:
        transaction = connection.begin()
        act_as(connection, "authenticated", claims_for(uuid4(), Role.registered_user))
        rows = connection.execute(text("SELECT id FROM public.authenticated_collection_runs")).all()
        transaction.rollback()

    assert rows == []
