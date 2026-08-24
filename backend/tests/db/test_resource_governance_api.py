"""Curated-resource lifecycle, roles, projection, and audit (B-S19)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DatabaseError

from amanah.domain.enums import Role
from amanah.main import create_app
from tests.conftest import make_access_token, make_settings

ADMIN_RESOURCES = "/v1/admin/resources"


@pytest.fixture
def application(database_url: str) -> Any:
    return create_app(make_settings(database_url=database_url))


def _client(application: Any, role: Role | None) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        if role is not None:
            token = make_access_token(application.state.settings, role=role)
            test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client


@pytest.fixture
def reviewer(application: Any) -> Iterator[TestClient]:
    yield from _client(application, Role.reviewer)


@pytest.fixture
def administrator(application: Any) -> Iterator[TestClient]:
    yield from _client(application, Role.administrator)


@pytest.fixture
def base_user(application: Any) -> Iterator[TestClient]:
    yield from _client(application, Role.registered_user)


@pytest.fixture
def anonymous(application: Any) -> Iterator[TestClient]:
    yield from _client(application, None)


def _resource_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": "Synthetic support resource",
        "organization": "Synthetic Civil Society Group",
        "url": f"https://example.test/resources/{uuid4()}",
        "country_scope": "CA",
        "category": "support_for_affected_people",
        "summary": "A reviewed synthetic description used only for catalog governance tests.",
    }
    body.update(overrides)
    return body


def _create(client: TestClient, **overrides: object) -> dict[str, Any]:
    response = client.post(ADMIN_RESOURCES, json=_resource_body(**overrides))
    assert response.status_code == 201
    return response.json()["resource"]


def test_anonymous_and_base_roles_cannot_manage_resources(
    anonymous: TestClient, base_user: TestClient
) -> None:
    assert anonymous.get(ADMIN_RESOURCES).status_code == 401
    assert base_user.get(ADMIN_RESOURCES).status_code == 403
    assert base_user.post(ADMIN_RESOURCES, json=_resource_body()).status_code == 403


def test_reviewers_and_administrators_create_drafts(
    reviewer: TestClient, administrator: TestClient
) -> None:
    assert _create(reviewer)["status"] == "draft"
    assert _create(administrator)["status"] == "draft"


def test_publication_requires_explicit_review_and_reaches_base_projection(
    reviewer: TestClient, base_user: TestClient
) -> None:
    resource = _create(reviewer, title="Reviewed catalog entry")
    resource_id = resource["id"]
    assert base_user.get("/v1/resources").json()["resources"] == []

    assert reviewer.post(f"{ADMIN_RESOURCES}/{resource_id}/publish", json={}).status_code == 400
    assert (
        reviewer.post(
            f"{ADMIN_RESOURCES}/{resource_id}/publish", json={"reviewed_summary": False}
        ).status_code
        == 400
    )

    published = reviewer.post(
        f"{ADMIN_RESOURCES}/{resource_id}/publish", json={"reviewed_summary": True}
    )
    assert published.status_code == 200
    managed = published.json()["resource"]
    assert managed["status"] == "published"
    assert UUID(managed["reviewed_by"])
    assert managed["last_reviewed_at"]
    assert [entry["title"] for entry in base_user.get("/v1/resources").json()["resources"]] == [
        "Reviewed catalog entry"
    ]


def test_changing_published_copy_returns_it_to_draft(
    reviewer: TestClient, base_user: TestClient
) -> None:
    resource = _create(reviewer)
    resource_id = resource["id"]
    reviewer.post(f"{ADMIN_RESOURCES}/{resource_id}/publish", json={"reviewed_summary": True})

    response = reviewer.patch(
        f"{ADMIN_RESOURCES}/{resource_id}",
        json={"summary": "A changed summary that must receive a fresh human review."},
    )

    assert response.status_code == 200
    assert response.json()["resource"]["status"] == "draft"
    assert response.json()["resource"]["reviewed_by"] is None
    assert base_user.get("/v1/resources").json()["resources"] == []


def test_archiving_removes_an_entry_and_audit_history_is_append_only(
    reviewer: TestClient, base_user: TestClient
) -> None:
    resource = _create(reviewer)
    resource_id = resource["id"]
    reviewer.patch(f"{ADMIN_RESOURCES}/{resource_id}", json={"country_scope": "global"})
    reviewer.post(f"{ADMIN_RESOURCES}/{resource_id}/publish", json={"reviewed_summary": True})
    archived = reviewer.post(f"{ADMIN_RESOURCES}/{resource_id}/archive")

    assert archived.status_code == 200
    assert archived.json()["resource"]["status"] == "archived"
    assert base_user.get("/v1/resources").json()["resources"] == []
    audit = reviewer.get(f"{ADMIN_RESOURCES}/{resource_id}/audit").json()["events"]
    assert [event["action"] for event in audit] == [
        "created",
        "updated",
        "published",
        "archived",
    ]
    assert all(event["snapshot"]["title"] == resource["title"] for event in audit)


@pytest.mark.parametrize(
    "overrides",
    [
        {"url": "http://example.test/resource"},
        {"url": "https://user:secret@example.test/resource"},
        {"url": "https://localhost/resource"},
        {"country_scope": "ZZ"},
        {"summary": "Too short"},
    ],
)
def test_invalid_resource_fields_are_rejected(
    reviewer: TestClient, overrides: dict[str, object]
) -> None:
    response = reviewer.post(ADMIN_RESOURCES, json=_resource_body(**overrides))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_duplicate_resource_urls_are_a_conflict(reviewer: TestClient) -> None:
    url = "https://example.test/resources/unique"
    _create(reviewer, url=url)

    response = reviewer.post(ADMIN_RESOURCES, json=_resource_body(url=url))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_CONFLICT"


def test_explicit_null_updates_are_rejected(reviewer: TestClient) -> None:
    resource = _create(reviewer)

    response = reviewer.patch(f"{ADMIN_RESOURCES}/{resource['id']}", json={"summary": None})

    assert response.status_code == 400


def test_resource_audit_history_cannot_be_rewritten(reviewer: TestClient, engine: Engine) -> None:
    resource = _create(reviewer)

    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DatabaseError, match="append_only_violation"):
            connection.execute(
                text(
                    "UPDATE public.resource_audit_events SET action = 'updated' "
                    "WHERE resource_entry_id = :resource_id"
                ),
                {"resource_id": resource["id"]},
            )
        transaction.rollback()
