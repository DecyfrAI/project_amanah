"""Synthetic rows for database tests.

Everything here is invented. No fixture reproduces real hateful text, a real
author, or a real URL: the excerpts are neutral placeholders, and what the tests
actually assert on is structure — provenance, constraints, ordering, and
visibility — not wording.

Each factory takes safe defaults and lets a test override only the field it is
about, so a schema change lands in one place.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, text

from amanah.domain.enums import (
    ApprovalStatus,
    CollectionMode,
    ConfidenceTier,
    ConnectorStatus,
    ContentKind,
    InferenceStatus,
    JobState,
    MetricInterval,
    PublicationStatus,
    PublicPlatform,
    Relevance,
    RetentionPolicy,
    ReviewState,
    SourceKind,
    SourceStatus,
    Stance,
)

#: Re-exported so a test can name a controlled value without a second import.
__all__ = ["InferenceStatus", "PublicPlatform", "PublicationStatus", "SourceKind"]

BASE_TIME = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

#: Deliberately bland. These tests are about plumbing, and storing realistic
#: hateful text to prove that a JOIN works would be gratuitous.
NEUTRAL_EXCERPT = "Synthetic placeholder text for tests."

SAMPLING_DISCLOSURE = "Synthetic monitored sample; not a population estimate."


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _insert(connection: Connection, table: str, values: dict[str, Any]) -> UUID:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    statement = text(f"INSERT INTO public.{table} ({columns}) VALUES ({placeholders}) RETURNING id")
    return UUID(str(connection.execute(statement, values).scalar_one()))


def insert_source(
    connection: Connection,
    *,
    source_key: str = "fixture_news",
    kind: SourceKind = SourceKind.news,
    platform: PublicPlatform = PublicPlatform.news_web,
    name: str = "Synthetic wire",
    status: ConnectorStatus = ConnectorStatus.ok,
    last_success_at: datetime | None = BASE_TIME,
    safe_warning: str | None = None,
    is_enabled: bool = True,
) -> UUID:
    return _insert(
        connection,
        "sources",
        {
            "source_key": source_key,
            "kind": kind.value,
            "platform": platform.value,
            "name": name,
            "purpose": "Synthetic source used by tests.",
            "config_version": "v1",
            "retention_policy": RetentionPolicy.limited_by_terms.value,
            "status": status.value,
            "is_enabled": is_enabled,
            "last_success_at": last_success_at,
            "last_checked_at": last_success_at,
            "safe_warning": safe_warning,
        },
    )


def insert_open_datapack_source(connection: Connection) -> UUID:
    """The single controlled row every datapack record points at.

    Its public name is `N/A`: a datapack row has no meaningful platform, and its
    lineage lives in the dataset columns instead.
    """
    return insert_source(
        connection,
        source_key="open_datapack",
        kind=SourceKind.open_datapack,
        platform=PublicPlatform.not_applicable,
        name="N/A",
        status=ConnectorStatus.disabled,
        last_success_at=None,
        is_enabled=False,
    )


def insert_seed_entry(
    connection: Connection,
    *,
    source_id: UUID,
    registry_key: str = "yt_query_001",
    config_version: str = "v1",
    item_cap: int = 50,
    language: str = "en",
    approval_status: ApprovalStatus = ApprovalStatus.approved,
) -> UUID:
    return _insert(
        connection,
        "source_seed_entries",
        {
            "registry_key": registry_key,
            "source_id": source_id,
            "entry_kind": "search_query",
            "display_name": "Synthetic approved query",
            "provider_reference": "synthetic query string",
            "query_family": "synthetic_family",
            "query_purpose": "Sampling relevance only; not a hate label.",
            "sampling_stratum": "boundary_control",
            "language": language,
            "item_cap": item_cap,
            "approval_status": approval_status.value,
            "approved_by": "test-reviewer",
            "config_version": config_version,
        },
    )


def insert_dataset_package(
    connection: Connection,
    *,
    provider: str = "synthetic-provider",
    name: str = "synthetic-dataset",
    version: str = "1.0.0",
    approval_status: ApprovalStatus = ApprovalStatus.approved,
    approved_by: str | None = "test-reviewer",
) -> UUID:
    return _insert(
        connection,
        "dataset_packages",
        {
            "provider": provider,
            "name": name,
            "version": version,
            "landing_page_url": "https://example.test/dataset",
            "license_id": "CC-BY-4.0",
            "permitted_uses": "Research use permitted by the reviewed licence.",
            "approval_status": approval_status.value,
            "approved_by": approved_by,
            "retrieved_at": BASE_TIME,
            "file_sha256": _hash(f"{provider}/{name}/{version}"),
            "schema_mapping_version": "v1",
        },
    )


def insert_collection_run(
    connection: Connection, *, source_id: UUID, idempotency_key: str | None = None
) -> UUID:
    return _insert(
        connection,
        "collection_runs",
        {
            "source_id": source_id,
            "idempotency_key": idempotency_key or f"run-{uuid4()}",
            "mode": CollectionMode.fixture.value,
            "adapter_version": "v1",
            "status": JobState.succeeded.value,
        },
    )


def insert_content_item(
    connection: Connection,
    *,
    source_id: UUID,
    source_item_id: str | None = None,
    content_kind: ContentKind = ContentKind.news_article,
    title: str | None = "Synthetic article title",
    permitted_excerpt: str | None = NEUTRAL_EXCERPT,
    observed_at: datetime = BASE_TIME,
    published_at: datetime | None = BASE_TIME,
    country_code: str | None = "CA",
    language: str | None = "en",
    dataset_package_id: UUID | None = None,
    dataset_row_id: str | None = None,
    dataset_import_run_id: UUID | None = None,
    review_state: ReviewState = ReviewState.model_only,
    is_fixture: bool = True,
    source_status: SourceStatus = SourceStatus.available,
    submitted_origin: UUID | None = None,
    normalized_text: str = "synthetic normalized text",
    text_ciphertext: bytes = b"synthetic-ciphertext",
    raw_object_key: str = "synthetic/object/key",
) -> UUID:
    identifier = source_item_id or f"item-{uuid4()}"
    return _insert(
        connection,
        "content_items",
        {
            "source_id": source_id,
            "source_item_id": identifier,
            "content_kind": content_kind.value,
            "canonical_url": f"https://example.test/{identifier}",
            "title": title,
            "permitted_excerpt": permitted_excerpt,
            # Present so the projection tests can prove these never surface.
            "normalized_text": normalized_text,
            "text_ciphertext": text_ciphertext,
            "raw_object_key": raw_object_key,
            "publisher_or_container": "Synthetic publisher",
            "published_at": published_at,
            "observed_at": observed_at,
            "language": language,
            "country_code": country_code,
            # One of the two values the news contract defines.
            "geographic_scope": "local",
            "source_status": source_status.value,
            "is_fixture": is_fixture,
            "submitted_origin": submitted_origin,
            "effective_review_state": review_state.value,
            "content_hash": _hash(identifier),
            "dataset_package_id": dataset_package_id,
            "dataset_row_id": dataset_row_id,
            "dataset_import_run_id": dataset_import_run_id,
        },
    )


def insert_prediction(
    connection: Connection,
    *,
    content_item_id: UUID,
    relevance: Relevance = Relevance.muslim_related,
    stance: Stance = Stance.non_hateful_discussion,
    severity: int = 0,
    score: float = 0.75,
    confidence_tier: ConfidenceTier = ConfidenceTier.medium,
    narrative_tags: tuple[str, ...] = ("policy_debate",),
    hate_types: tuple[str, ...] = (),
    model_version: str = "v1",
    prompt_version: str = "p1",
    inference_status: InferenceStatus = InferenceStatus.succeeded,
    requires_review: bool = False,
    created_at: datetime | None = None,
) -> UUID:
    values: dict[str, Any] = {
        "content_item_id": content_item_id,
        "model_name": "synthetic-model",
        "model_version": model_version,
        "prompt_version": prompt_version,
        "taxonomy_version": "t1",
        "relevance": relevance.value,
        "stance": stance.value,
        "hate_types": list(hate_types),
        "severity": severity,
        "narrative_tags": list(narrative_tags),
        "score": score,
        "confidence_tier": confidence_tier.value,
        "confidence_threshold_version": "thresholds-v1",
        "rationale": "Synthetic rationale.",
        "requires_review": requires_review,
        "inference_status": inference_status.value,
        "inferred_at": BASE_TIME,
    }
    if created_at is not None:
        values["created_at"] = created_at
    return _insert(connection, "predictions", values)


def insert_metric_bucket(
    connection: Connection,
    *,
    source_id: UUID,
    metric_key: str = "likely_anti_muslim_rate",
    bucket_start: datetime = BASE_TIME,
    interval: MetricInterval = MetricInterval.daily,
    observed_count: int = 10,
    relevant_count: int = 6,
    likely_hate_count: int = 2,
    reviewed_count: int = 1,
    confirmed_count: int = 1,
    filter_version: str = "f1",
    coverage_score: float | None = 0.9,
) -> UUID:
    return _insert(
        connection,
        "metric_buckets",
        {
            "metric_key": metric_key,
            "source_id": source_id,
            "interval": interval.value,
            "bucket_start": bucket_start,
            "observed_count": observed_count,
            "relevant_count": relevant_count,
            "likely_hate_count": likely_hate_count,
            "reviewed_count": reviewed_count,
            "confirmed_count": confirmed_count,
            "coverage_score": coverage_score,
            "filter_version": filter_version,
            "sampling_disclosure": SAMPLING_DISCLOSURE,
        },
    )


def insert_resource_entry(
    connection: Connection,
    *,
    title: str = "Synthetic resource",
    url: str | None = None,
    status: PublicationStatus = PublicationStatus.published,
    category: str = "understanding_islamophobia",
    country_scope: str = "global",
) -> UUID:
    reviewed = status is PublicationStatus.published
    return _insert(
        connection,
        "resource_entries",
        {
            "title": title,
            "organization": "Synthetic Organisation",
            "url": url or f"https://example.test/resource/{uuid4()}",
            "country_scope": country_scope,
            "category": category,
            "summary": "Synthetic summary of a reviewed resource.",
            "status": status.value,
            "last_reviewed_at": BASE_TIME if reviewed else None,
            "reviewed_by": "test-reviewer" if reviewed else None,
        },
    )


def insert_contribution_event(
    connection: Connection,
    *,
    user_id: UUID,
    contribution_id: UUID | None = None,
    public_message: str = "Synthetic contribution update.",
) -> UUID:
    return _insert(
        connection,
        "contribution_events",
        {
            "user_id": user_id,
            "contribution_type": "url_submission",
            "contribution_id": contribution_id or uuid4(),
            "event_type": "created",
            "public_message": public_message,
        },
    )


def insert_user_profile(
    connection: Connection, *, user_id: UUID, role: str = "registered_user"
) -> UUID:
    connection.execute(
        text(
            "INSERT INTO public.user_profiles (user_id, display_name, role) "
            "VALUES (:user_id, :display_name, :role)"
        ),
        {"user_id": user_id, "display_name": "Synthetic user", "role": role},
    )
    return user_id


def insert_platform_policy(
    connection: Connection,
    *,
    platform: str = "youtube",
    policy_key: str = "hate_speech",
    version: str = "2026.08.23",
    status: PublicationStatus = PublicationStatus.published,
    recipient_kind: str = "official_form",
    official_report_url: str | None = "https://example.test/report",
    report_email: str | None = None,
) -> UUID:
    reviewed = status is PublicationStatus.published
    return _insert(
        connection,
        "platform_policies",
        {
            "platform": platform,
            "policy_key": policy_key,
            "title": "Synthetic platform rule",
            "official_url": f"https://example.test/policy/{policy_key}",
            "summary": "Synthetic summary of a reviewed platform rule.",
            "version": version,
            "last_reviewed_at": BASE_TIME if reviewed else None,
            "status": status.value,
            "reviewed_by": "test-reviewer" if reviewed else None,
            "recipient_kind": recipient_kind,
            "official_report_url": official_report_url,
            "report_email": report_email,
        },
    )


def insert_review_task(
    connection: Connection,
    *,
    content_item_id: UUID,
    prediction_id: UUID,
    task_type: str = "dispute",
    status: str = "open",
    priority: int = 100,
    assigned_to: UUID | None = None,
) -> UUID:
    return _insert(
        connection,
        "review_tasks",
        {
            "content_item_id": content_item_id,
            "prediction_id": prediction_id,
            "task_type": task_type,
            "reason": "Synthetic reason for review.",
            "priority": priority,
            "status": status,
            "assigned_to": assigned_to,
        },
    )


def insert_snapshot_insight(
    connection: Connection,
    *,
    user_id: UUID,
    title: str = "Synthetic snapshot",
    numerator: int = 12,
    denominator: int = 400,
    created_at: datetime | None = None,
) -> UUID:
    values: dict[str, Any] = {
        "user_id": user_id,
        "title": title,
        "claim": "12 of 400 monitored items were classified likely anti-Muslim.",
        "metric": "likely_anti_muslim_rate",
        "numerator": numerator,
        "denominator": denominator,
        "window_start": BASE_TIME,
        "window_end": BASE_TIME + timedelta(days=7),
        "figure_label": "Daily rate",
        "filter_hash": "a1b2c3d4e5f60718",
        "explorer_href": "/app/explorer?from=2026-06-01",
        "source_keys": ["fixtures"],
        "items_observed": 400,
        "items_relevant": 120,
    }
    if created_at is not None:
        values["created_at"] = created_at
    return _insert(connection, "snapshot_insights", values)


def insert_dashboard_capture(connection: Connection, *, user_id: UUID) -> UUID:
    return _insert(
        connection,
        "dashboard_captures",
        {
            "user_id": user_id,
            "alt_text": "Synthetic figure showing a daily rate.",
            "image_source": "/media/figures/synthetic.png",
            "filter_hash": "a1b2c3d4e5f60718",
            "explorer_href": "/app/explorer?from=2026-06-01",
        },
    )


def insert_discussion_participant(
    connection: Connection, *, user_id: UUID, granted_by: UUID | None = None
) -> UUID:
    return _insert(
        connection,
        "discussion_participants",
        {"user_id": user_id, "granted_by": granted_by or uuid4()},
    )


def insert_discussion_post(
    connection: Connection,
    *,
    snapshot_insight_id: UUID,
    user_id: UUID,
    body: str = "Synthetic note about a figure.",
    dashboard_capture_id: UUID | None = None,
) -> UUID:
    return _insert(
        connection,
        "discussion_posts",
        {
            "snapshot_insight_id": snapshot_insight_id,
            "user_id": user_id,
            "body": body,
            "dashboard_capture_id": dashboard_capture_id,
        },
    )


def days_after(count: int) -> datetime:
    """A timestamp offset from the shared base, for ordering assertions."""
    return BASE_TIME + timedelta(days=count)
