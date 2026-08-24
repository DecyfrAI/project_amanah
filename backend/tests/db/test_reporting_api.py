"""Policy analysis and prepared platform reports (B-S18.2 to B-S18.9).

The most important assertions here are negative. Nothing this module exercises
may reach a platform, accept a recipient from a caller, or claim that a report
was received; and content the classifier did not read as anti-Muslim gets no
policy match at all.
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
    PublicPlatform,
    Relevance,
    Severity,
    SourceKind,
    Stance,
)
from amanah.main import create_app
from amanah.settings import Settings
from tests.conftest import make_access_token, make_settings
from tests.db import factories

REPORTS = "/v1/prepared-reports"

OWNER = UUID("66666666-6666-6666-6666-666666666666")
STRANGER = UUID("77777777-7777-7777-7777-777777777777")

ALLOW_LISTED = "reviewers@example.invalid"


@pytest.fixture
def api_settings(database_url: str) -> Settings:
    return make_settings(database_url=database_url)


def _client_for(settings: Settings, user_id: UUID) -> TestClient:
    client = TestClient(create_app(settings))
    client.headers["Authorization"] = f"Bearer {make_access_token(settings, user_id=user_id)}"
    return client


@pytest.fixture
def owner(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, OWNER) as client:
        yield client


@pytest.fixture
def stranger(api_settings: Settings) -> Iterator[TestClient]:
    with _client_for(api_settings, STRANGER) as client:
        yield client


def _seed_item(
    connection: Any,
    *,
    stance: Stance = Stance.likely_anti_muslim,
    hate_types: tuple[str, ...] = (HateType.derogation.value,),
    severity: int = int(Severity.moderate),
    source_key: str = "fixture_youtube",
) -> UUID:
    source_id = factories.insert_source(
        connection,
        source_key=source_key,
        kind=SourceKind.social,
        platform=PublicPlatform.youtube,
        name="Synthetic video platform",
    )
    item_id = factories.insert_content_item(connection, source_id=source_id)
    factories.insert_prediction(
        connection,
        content_item_id=item_id,
        relevance=Relevance.muslim_related,
        stance=stance,
        hate_types=hate_types,
        severity=severity,
        confidence_tier=ConfidenceTier.medium,
    )
    return item_id


@pytest.fixture
def reportable(engine: Engine) -> dict[str, Any]:
    """One classified YouTube item and a published policy that could apply."""
    with engine.begin() as connection:
        item_id = _seed_item(connection)
        policy_id = factories.insert_platform_policy(connection)
    return {"item_id": item_id, "policy_id": policy_id}


# -- policy analysis ------------------------------------------------------


def test_analysis_offers_only_reviewed_rules_and_never_claims_certainty(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    """FR-TOS-001 and FR-TOS-002: catalogued rules, official links, review dates,
    and language that stays a possibility."""
    body = owner.post(f"/v1/items/{reportable['item_id']}/policy-analysis").json()

    assert body["candidates"], "a classified item should have at least one candidate"
    for candidate in body["candidates"]:
        assert candidate["official_url"].startswith("https://")
        assert candidate["last_reviewed_at"] is not None
        assert "Possible match" in candidate["rationale"]
        assert candidate["score"] < 1.0
    assert "not findings" in body["disclosure"]


def test_a_draft_policy_is_never_offered(owner: TestClient, engine: Engine) -> None:
    """An unreviewed summary must not reach a user as curation."""
    with engine.begin() as connection:
        item_id = _seed_item(connection, source_key="fixture_youtube_draft")
        factories.insert_platform_policy(
            connection,
            policy_key="unreviewed_rule",
            status=factories.PublicationStatus.draft,
        )

    body = owner.post(f"/v1/items/{item_id}/policy-analysis").json()

    assert [c["policy_key"] for c in body["candidates"]] == []


@pytest.mark.parametrize(
    "stance",
    [Stance.counterspeech_or_quotation, Stance.non_hateful_discussion, Stance.uncertain],
)
def test_content_that_is_not_anti_muslim_gets_no_policy_match(
    owner: TestClient, engine: Engine, stance: Stance
) -> None:
    """`AGENTS.md`: never treat Muslim-related language as hateful by default.
    Offering a reporting flow for counterspeech or a quotation would turn the
    assistant into a way to report people for discussing the subject."""
    with engine.begin() as connection:
        item_id = _seed_item(connection, stance=stance, source_key=f"fixture_{stance.value}")
        factories.insert_platform_policy(connection)

    body = owner.post(f"/v1/items/{item_id}/policy-analysis").json()

    assert body["candidates"] == []


def test_an_unclassified_item_cannot_be_analysed(owner: TestClient, engine: Engine) -> None:
    with engine.begin() as connection:
        source_id = factories.insert_source(connection, source_key="fixture_bare")
        item_id = factories.insert_content_item(connection, source_id=source_id)

    assert owner.post(f"/v1/items/{item_id}/policy-analysis").status_code == 422


# -- preparation ----------------------------------------------------------


def _prepare(client: TestClient, reportable: dict[str, Any], **overrides: Any) -> Any:
    payload: dict[str, Any] = {
        "content_item_id": str(reportable["item_id"]),
        "platform_policy_id": str(reportable["policy_id"]),
        "policy_version": "2026.08.23",
        "evidence_summary": "Synthetic evidence summary.",
        "suggested_text": "Synthetic suggested wording.",
    }
    payload.update(overrides)
    return client.post(REPORTS, json=payload)


def test_a_prepared_report_freezes_the_confirmed_policy_version(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    """FR-TOS-007: the version travels with the record so a later re-review
    cannot rewrite what the user was shown."""
    response = _prepare(owner, reportable)

    assert response.status_code == 201
    report = response.json()["report"]
    assert report["policy_version"] == "2026.08.23"
    assert report["status"] == "prepared"
    assert report["submitted_at"] is None
    assert report["outcome"] is None


def test_a_stale_policy_version_is_a_conflict_rather_than_a_substitution(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    """B-S18.8. The wording the user wrote was about the version they read."""
    response = _prepare(owner, reportable, policy_version="2020.01.01")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESOURCE_CONFLICT"


def test_a_form_platform_draft_carries_no_recipient(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    """FR-TOS-010: a platform with a reporting form gets the catalogue flow, and
    a record with an address would imply a message we never send."""
    report = _prepare(owner, reportable).json()["report"]

    assert report["recipient_kind"] == "official_form"
    assert report["recipient_address"] is None
    assert report["draft_subject"] is None


def test_a_form_platform_refuses_a_subject_line(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    response = _prepare(owner, reportable, draft_subject="Reporting a video")

    assert response.status_code == 422


def test_an_email_draft_uses_only_the_allow_listed_address(
    owner: TestClient, engine: Engine
) -> None:
    """FR-TOS-010. The address comes from the reviewed catalogue; a caller has no
    field to put one in, and the record shows the reviewed value."""
    with engine.begin() as connection:
        item_id = _seed_item(connection, source_key="fixture_no_form")
        policy_id = factories.insert_platform_policy(
            connection,
            platform="youtube",
            policy_key="no_official_form",
            recipient_kind="allowlist_email",
            official_report_url=None,
            report_email=ALLOW_LISTED,
        )

    response = _prepare(
        owner,
        {"item_id": item_id, "policy_id": policy_id},
        draft_subject="Possible policy match for review",
    )

    report = response.json()["report"]
    assert response.status_code == 201
    assert report["recipient_kind"] == "allowlist_email"
    assert report["recipient_address"] == ALLOW_LISTED
    assert report["draft_subject"] == "Possible policy match for review"


def test_an_email_draft_without_a_subject_is_refused(owner: TestClient, engine: Engine) -> None:
    with engine.begin() as connection:
        item_id = _seed_item(connection, source_key="fixture_no_form_two")
        policy_id = factories.insert_platform_policy(
            connection,
            policy_key="no_official_form_two",
            recipient_kind="allowlist_email",
            official_report_url=None,
            report_email=ALLOW_LISTED,
        )

    response = _prepare(owner, {"item_id": item_id, "policy_id": policy_id})

    assert response.status_code == 422


def test_preparing_the_same_report_twice_is_refused_as_brigading(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    """FR-TOS-009: one prepared report per person, item, and platform."""
    assert _prepare(owner, reportable).status_code == 201

    second = _prepare(owner, reportable)

    assert second.status_code == 409


# -- outcomes -------------------------------------------------------------


def test_the_user_may_record_that_they_filed_it_and_what_followed(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    """FR-TOS-008. `submitted_at` is the user's own account, never a receipt."""
    report = _prepare(owner, reportable).json()["report"]

    submitted = owner.patch(f"{REPORTS}/{report['id']}", json={"status": "submitted"}).json()
    assert submitted["report"]["submitted_at"] is not None

    closed = owner.patch(
        f"{REPORTS}/{report['id']}",
        json={"status": "closed", "outcome": "content_removed", "outcome_note": "Taken down."},
    ).json()
    assert closed["report"]["status"] == "closed"
    assert closed["report"]["outcome"] == "content_removed"


def test_a_report_cannot_be_closed_before_it_was_filed(
    owner: TestClient, reportable: dict[str, Any]
) -> None:
    report = _prepare(owner, reportable).json()["report"]

    response = owner.patch(
        f"{REPORTS}/{report['id']}", json={"status": "closed", "outcome": "no_response"}
    )

    assert response.status_code == 409


def test_a_closed_report_is_final(owner: TestClient, reportable: dict[str, Any]) -> None:
    report = _prepare(owner, reportable).json()["report"]
    owner.patch(f"{REPORTS}/{report['id']}", json={"status": "submitted"})
    owner.patch(f"{REPORTS}/{report['id']}", json={"status": "closed", "outcome": "no_response"})

    response = owner.patch(f"{REPORTS}/{report['id']}", json={"status": "submitted"})

    assert response.status_code == 409


def test_another_user_cannot_record_an_outcome(
    owner: TestClient, stranger: TestClient, reportable: dict[str, Any]
) -> None:
    report = _prepare(owner, reportable).json()["report"]

    response = stranger.patch(f"{REPORTS}/{report['id']}", json={"status": "submitted"})

    assert response.status_code == 422
    assert "not found" in response.json()["error"]["message"]


def test_an_anonymous_caller_cannot_prepare_a_report(
    api_settings: Settings, reportable: dict[str, Any]
) -> None:
    with TestClient(create_app(api_settings)) as client:
        assert client.post(REPORTS, json={}).status_code == 401
        assert client.post(f"/v1/items/{reportable['item_id']}/policy-analysis").status_code == 401


def test_no_external_side_effect_is_recorded_anywhere(
    owner: TestClient, reportable: dict[str, Any], engine: Engine
) -> None:
    """FR-TOS-006. There is no column in this schema that could hold a platform
    acknowledgement, and nothing writes one."""
    _prepare(owner, reportable)

    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'prepared_platform_reports'"
                )
            ).scalars()
        )

    forbidden = {"platform_acknowledged_at", "delivery_status", "sent_at", "platform_ticket_id"}
    assert not (columns & forbidden)


def test_an_unknown_item_cannot_be_reported(owner: TestClient, reportable: dict[str, Any]) -> None:
    response = _prepare(owner, {**reportable, "item_id": uuid4()})

    assert response.status_code == 422
