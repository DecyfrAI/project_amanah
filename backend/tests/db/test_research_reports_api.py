"""Immutable aggregate research-report snapshots and exports (B-S20)."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DatabaseError

from amanah.domain.enums import ConfidenceTier, Relevance, Role, Stance
from amanah.main import create_app
from tests.conftest import make_access_token, make_settings
from tests.db import factories

REPORTS = "/v1/research-reports"


@pytest.fixture
def application(database_url: str) -> Any:
    return create_app(make_settings(database_url=database_url))


def _client(application: Any, *, user_id: UUID, role: Role) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        token = make_access_token(application.state.settings, user_id=user_id, role=role)
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def owner(application: Any, owner_id: UUID) -> Iterator[TestClient]:
    yield from _client(application, user_id=owner_id, role=Role.registered_user)


@pytest.fixture
def stranger(application: Any) -> Iterator[TestClient]:
    yield from _client(application, user_id=uuid4(), role=Role.registered_user)


@pytest.fixture
def reviewer(application: Any) -> Iterator[TestClient]:
    yield from _client(application, user_id=uuid4(), role=Role.reviewer)


@pytest.fixture
def seeded(engine: Engine) -> dict[str, UUID]:
    with engine.begin() as connection:
        source_id = factories.insert_source(connection)
        first = factories.insert_content_item(connection, source_id=source_id, country_code="CA")
        factories.insert_prediction(
            connection,
            content_item_id=first,
            relevance=Relevance.muslim_related,
            stance=Stance.likely_anti_muslim,
            confidence_tier=ConfidenceTier.high,
            score=0.92,
        )
        second = factories.insert_content_item(
            connection,
            source_id=source_id,
            country_code="CA",
            observed_at=factories.days_after(1),
        )
        factories.insert_prediction(
            connection,
            content_item_id=second,
            relevance=Relevance.muslim_related,
            stance=Stance.non_hateful_discussion,
        )
        factories.insert_metric_bucket(connection, source_id=source_id)
    return {"source_id": source_id, "first": first, "second": second}


def _report_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": "Synthetic filtered research report",
        "filters": {"country_codes": ["CA"]},
        "metrics": ["observed_count", "likely_anti_muslim_rate"],
        "findings": ["monitored_sample_rate", "analysis_coverage"],
        "include_aggregate_csv": True,
        "redaction_mode": "aggregate_only",
    }
    body.update(overrides)
    return body


def _create(owner: TestClient, **overrides: object) -> dict[str, Any]:
    response = owner.post(REPORTS, json=_report_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()["report"]


def test_report_freezes_filters_versions_metrics_findings_and_citations(
    owner: TestClient, seeded: dict[str, UUID]
) -> None:
    del seeded
    report = _create(owner)

    assert report["filters"]["country_codes"] == ["CA"]
    assert report["data_version"].startswith("data-")
    assert report["methodology_version"]
    assert report["coverage"]["coverage_score"] == 1.0
    assert report["status"] == "ready"
    assert report["redaction_mode"] == "aggregate_only"
    rate = next(
        metric for metric in report["metrics"] if metric["key"] == "likely_anti_muslim_rate"
    )
    assert rate["numerator"] == 1
    assert rate["denominator"] == 2
    citation_ids = {citation["id"] for citation in report["citations"]}
    assert citation_ids
    assert all(set(finding["citation_ids"]) <= citation_ids for finding in report["findings"])


def test_report_projection_contains_no_raw_evidence_or_author_fields(
    owner: TestClient, seeded: dict[str, UUID]
) -> None:
    del seeded
    response = owner.post(REPORTS, json=_report_body())

    assert response.status_code == 201
    for forbidden in (
        "normalized_text",
        "text_ciphertext",
        "raw_object_key",
        "source_item_id",
        "author",
        factories.NEUTRAL_EXCERPT,
    ):
        assert forbidden not in response.text


def test_owner_and_reviewer_can_read_but_another_user_cannot(
    owner: TestClient,
    stranger: TestClient,
    reviewer: TestClient,
    seeded: dict[str, UUID],
) -> None:
    del seeded
    report_id = _create(owner)["id"]

    assert owner.get(f"{REPORTS}/{report_id}").status_code == 200
    assert reviewer.get(f"{REPORTS}/{report_id}").status_code == 200
    assert stranger.get(f"{REPORTS}/{report_id}").status_code == 404


def test_anonymous_report_access_is_denied(application: Any, seeded: dict[str, UUID]) -> None:
    del seeded
    with TestClient(application) as anonymous:
        assert anonymous.post(REPORTS, json=_report_body()).status_code == 401
        assert anonymous.get(f"{REPORTS}/{uuid4()}").status_code == 401


def test_csv_uses_the_stored_snapshot_not_changed_live_rows(
    owner: TestClient, seeded: dict[str, UUID], engine: Engine
) -> None:
    report = _create(owner)
    with engine.begin() as connection:
        later = factories.insert_content_item(
            connection,
            source_id=seeded["source_id"],
            country_code="CA",
            observed_at=factories.days_after(2),
        )
        factories.insert_prediction(
            connection,
            content_item_id=later,
            relevance=Relevance.muslim_related,
            stance=Stance.likely_anti_muslim,
        )

    response = owner.get(f"{REPORTS}/{report['id']}/summary.csv")

    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert list(rows[0]) == [
        "metric_key",
        "value",
        "numerator",
        "denominator",
        "window_start",
        "window_end",
        "source_scope",
        "coverage_score",
        "data_version",
        "methodology_version",
        "data_mode",
        "redaction_mode",
    ]
    rate = next(row for row in rows if row["metric_key"] == "likely_anti_muslim_rate")
    assert rate["numerator"] == "1"
    assert rate["denominator"] == "2"
    assert rate["data_version"] == report["data_version"]


def test_csv_must_have_been_included_in_snapshot_scope(
    owner: TestClient, seeded: dict[str, UUID]
) -> None:
    del seeded
    report = _create(owner, include_aggregate_csv=False)

    response = owner.get(f"{REPORTS}/{report['id']}/summary.csv")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_regeneration_always_creates_a_new_snapshot(
    owner: TestClient, seeded: dict[str, UUID], engine: Engine
) -> None:
    first = _create(owner)
    with engine.begin() as connection:
        later = factories.insert_content_item(
            connection,
            source_id=seeded["source_id"],
            country_code="CA",
            observed_at=factories.days_after(2),
        )
        factories.insert_prediction(
            connection,
            content_item_id=later,
            relevance=Relevance.muslim_related,
            stance=Stance.non_hateful_discussion,
        )
    second = _create(owner)

    assert first["id"] != second["id"]
    assert first["filter_hash"] == second["filter_hash"]
    assert first["data_version"] != second["data_version"]


def test_generation_and_download_are_audited(
    owner: TestClient, owner_id: UUID, seeded: dict[str, UUID], engine: Engine
) -> None:
    del seeded
    report = _create(owner)
    owner.get(f"{REPORTS}/{report['id']}/summary.csv")

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT actor_user_id, action, request_id "
                "FROM public.research_report_audit_events "
                "WHERE research_report_id = :report_id ORDER BY created_at, id"
            ),
            {"report_id": report["id"]},
        ).mappings()
        events = list(rows)

    assert [event["action"] for event in events] == ["generated", "downloaded"]
    assert all(UUID(str(event["actor_user_id"])) == owner_id for event in events)
    assert all(event["request_id"].startswith("req_") for event in events)


def test_invalid_report_filters_and_duplicate_selections_are_rejected(
    owner: TestClient, seeded: dict[str, UUID]
) -> None:
    del seeded
    too_wide = owner.post(
        REPORTS,
        json=_report_body(
            filters={
                "date_from": "2020-01-01T00:00:00Z",
                "date_to": "2026-01-01T00:00:00Z",
            }
        ),
    )
    duplicate = owner.post(
        REPORTS,
        json=_report_body(metrics=["observed_count", "observed_count"]),
    )

    assert too_wide.status_code == 400
    assert duplicate.status_code == 400


def test_report_audit_history_cannot_be_deleted(
    owner: TestClient, seeded: dict[str, UUID], engine: Engine
) -> None:
    del seeded
    report = _create(owner)

    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DatabaseError, match="append_only_violation"):
            connection.execute(
                text(
                    "DELETE FROM public.research_report_audit_events "
                    "WHERE research_report_id = :report_id"
                ),
                {"report_id": report["id"]},
            )
        transaction.rollback()
