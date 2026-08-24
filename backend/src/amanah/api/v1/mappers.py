"""Translation from projection rows into the published `/v1` models.

One place builds an item response. Adding a column to a projection therefore
does not leak it: it has to be named here first, and every route shares this
mapping so the item on a list, on a headline card, and on the detail page cannot
disagree about what an item is.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import Row

from amanah.api.schemas.connections import ConnectionState
from amanah.api.schemas.contributions import (
    ContributionEventEntry,
    ContributionSummary,
    DisputeSummary,
    SubmissionSummary,
)
from amanah.api.schemas.dashboard import HeadlineCard
from amanah.api.schemas.discussion import (
    CaptureSummary,
    DiscussionPostEntry,
    InsightSummary,
    PostReactionCounts,
    ViewerPostEntry,
)
from amanah.api.schemas.items import DatasetProvenance, ItemDetail, ItemSummary
from amanah.api.schemas.news import NewsItem
from amanah.api.schemas.reporting import PreparedReportSummary
from amanah.api.schemas.resources import ResourceEntry
from amanah.api.schemas.review import ReviewDecisionEntry, ReviewTaskSummary
from amanah.api.schemas.runs import BackgroundJobSummary, CollectionRunSummary
from amanah.domain.enums import NewsScope, ReactionKind

#: Shown on the item page beside any classification, so a reader meets the
#: limitation at the same moment as the label.
ITEM_LIMITATIONS = (
    "Labels come from an automated model and may be wrong; confidence tiers are "
    "provisional until calibrated against a reviewed holdout set.",
    "Absence of a label means the item has not been analysed, not that it is safe.",
    "Geography is recorded only when the source states it explicitly.",
)

#: `spec.md` section 9.5. Repeated wherever a rate or an item is shown, because
#: the sample is deliberately enriched and must never be read as prevalence.
SAMPLING_DISCLOSURE = (
    "These items come from a monitored sample selected for research relevance, "
    "not from a random draw. Counts and rates describe this sample only and are "
    "not a measure of any platform's or population's views."
)


def _dataset_provenance(row: Row[Any]) -> DatasetProvenance | None:
    """Dataset lineage, or `None` for an item that did not come from a datapack."""
    if row.dataset_provider is None:
        return None
    return DatasetProvenance(
        provider=row.dataset_provider,
        name=row.dataset_name,
        version=row.dataset_version,
        license_id=row.dataset_license_id,
        landing_page_url=row.dataset_landing_page_url,
    )


def _summary_fields(row: Row[Any]) -> dict[str, Any]:
    return {
        "id": row.id,
        "content_kind": row.content_kind,
        "platform": row.platform,
        "title": row.title,
        "permitted_excerpt": row.permitted_excerpt,
        "publisher_or_container": row.publisher_or_container,
        "canonical_url": row.canonical_url,
        "published_at": row.published_at,
        "observed_at": row.observed_at,
        "language": row.language,
        "country_code": row.country_code,
        "source_status": row.source_status,
        "is_fixture": row.is_fixture,
        "dataset": _dataset_provenance(row),
        "relevance": row.relevance,
        "stance": row.stance,
        "hate_types": list(row.hate_types or ()),
        "severity": row.severity,
        "confidence_tier": row.confidence_tier,
        "review_state": row.review_state,
        "requires_review": bool(row.requires_review),
    }


def to_item_summary(row: Row[Any]) -> ItemSummary:
    """Project one row onto the list and card model."""
    return ItemSummary(**_summary_fields(row))


def to_item_detail(row: Row[Any]) -> ItemDetail:
    """Project one row onto the item page model, with the model disclosure."""
    return ItemDetail(
        **_summary_fields(row),
        score=row.score,
        model_name=row.model_name,
        model_version=row.model_version,
        prompt_version=row.prompt_version,
        taxonomy_version=row.taxonomy_version,
        inferred_at=row.inferred_at,
        rationale=row.rationale,
        narrative_tags=list(row.narrative_tags or ()),
        limitations=list(ITEM_LIMITATIONS),
        sampling_disclosure=SAMPLING_DISCLOSURE,
    )


def to_headline_card(row: Row[Any]) -> HeadlineCard:
    """Project one news row onto a dashboard headline card.

    The summary is the permitted excerpt. When licensing did not allow one, the
    card says so rather than showing an empty box or inventing a summary.
    """
    return HeadlineCard(
        item_id=row.id,
        headline=row.title or "Untitled article",
        source_name=row.publisher_or_container or row.source_name,
        published_at=row.published_at,
        country_code=row.country_code,
        geographic_scope=row.geographic_scope,
        summary=row.permitted_excerpt or "No excerpt is available under this source's terms.",
        topic_labels=list(row.narrative_tags or ()),
    )


def to_resource_entry(row: Row[Any]) -> ResourceEntry:
    """Project one published catalogue row."""
    return ResourceEntry(
        id=row.id,
        title=row.title,
        organization=row.organization,
        url=row.url,
        country_scope=row.country_scope,
        category=row.category,
        summary=row.summary,
        last_reviewed_at=row.last_reviewed_at,
    )


def to_connection_state(row: Row[Any]) -> ConnectionState:
    """Project one source row onto its safe connector state."""
    return ConnectionState(
        source_key=row.source_key,
        name=row.name,
        kind=row.kind,
        platform=row.platform,
        purpose=row.purpose,
        policy_url=row.policy_url,
        status=row.status,
        is_enabled=row.is_enabled,
        last_success_at=row.last_success_at,
        last_checked_at=row.last_checked_at,
        warning=row.safe_warning,
    )


def to_collection_run(row: Row[Any]) -> CollectionRunSummary:
    """Build the administrator view of one run.

    `counts` and `coverage_warnings` are stored as JSON, so they are rebuilt into
    typed values here rather than passed through: a malformed count would
    otherwise reach an operator's screen as whatever the writer happened to put
    there.
    """
    return CollectionRunSummary(
        id=row.id,
        source_id=row.source_id,
        source_key=row.source_key,
        source_name=row.source_name,
        source_seed_entry_id=row.source_seed_entry_id,
        idempotency_key=row.idempotency_key,
        mode=row.mode,
        adapter_version=row.adapter_version,
        window_start=row.window_start,
        window_end=row.window_end,
        status=row.status,
        counts={str(key): int(value) for key, value in (row.counts or {}).items()},
        coverage_warnings=[str(warning) for warning in (row.coverage_warnings or [])],
        safe_error_code=row.safe_error_code,
        item_cap=row.item_cap,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        next_run_at=row.next_run_at,
        is_dead_lettered=row.is_dead_lettered,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def to_background_job(row: Row[Any]) -> BackgroundJobSummary:
    """Build the administrator view of one pipeline stage."""
    return BackgroundJobSummary(
        id=row.id,
        collection_run_id=row.collection_run_id,
        stage=row.stage,
        state=row.state,
        attempt=row.attempt,
        max_attempts=row.max_attempts,
        available_at=row.available_at,
        safe_error_code=row.safe_error_code,
        is_dead_lettered=row.is_dead_lettered,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def to_news_item(row: Row[Any]) -> NewsItem:
    """Build one context-news entry.

    Two fields are filled in rather than left blank, and both are truthful
    substitutions rather than guesses. `source_homepage` falls back to the
    article's own origin, which is the publisher's home page by definition.
    `summary` falls back to the headline, because the frontend contract requires
    a string and an empty one would render as a blank line under the title.

    `published_at` is deliberately *not* substituted. When a feed gave no
    publication date it stays null: claiming an article was published at the
    moment we retrieved it would be a fact the product invented.
    """
    return NewsItem(
        id=row.id,
        source_name=row.source_name,
        source_homepage=row.source_homepage or _origin(row.url),
        title=row.title or "",
        summary=row.summary or row.title or "",
        url=row.url,
        published_at=row.published_at,
        retrieved_at=row.retrieved_at,
        language=row.language or "en",
        scope=_news_scope(row.scope),
        location=row.country_code,
    )


def _news_scope(stored: str | None) -> NewsScope | None:
    """Read the stored scope, or report it absent.

    `geographic_scope` is free text shared with other content kinds. A value
    outside the two the news contract defines becomes `None`, because rounding an
    unknown scope to whichever looks closer would publish a claim about reach
    that no source made.
    """
    try:
        return NewsScope(stored) if stored else None
    except ValueError:
        return None


def _origin(url: str | None) -> str:
    """The scheme and host of a URL, used as a publisher home page."""
    if not url:
        return ""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.netloc else ""


def to_submission(row: Row[Any]) -> SubmissionSummary:
    """One URL submission as its owner sees it."""
    return SubmissionSummary(
        id=row.id,
        submitted_url=row.submitted_url,
        canonical_url=row.canonical_url,
        content_item_id=row.content_item_id,
        status=row.status,
        safe_error_code=row.safe_error_code,
        submitted_at=row.submitted_at,
        processed_at=row.processed_at,
    )


def to_dispute(row: Row[Any]) -> DisputeSummary:
    """One dispute as its owner sees it. The reviewer's private note is not here."""
    return DisputeSummary(
        id=row.id,
        content_item_id=row.content_item_id,
        prediction_id=row.prediction_id,
        reason=row.reason,
        status=row.status,
        resolution_summary=row.resolution_summary,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


def to_prepared_report(row: Row[Any]) -> PreparedReportSummary:
    """One prepared report. No field here can claim the platform received it."""
    return PreparedReportSummary(
        id=row.id,
        content_item_id=row.content_item_id,
        platform=row.platform,
        platform_policy_id=row.platform_policy_id,
        policy_version=row.policy_version,
        evidence_summary=row.evidence_summary,
        suggested_text=row.suggested_text,
        status=row.status,
        recipient_kind=row.recipient_kind,
        recipient_address=row.recipient_address,
        draft_subject=row.draft_subject,
        submitted_at=row.submitted_at,
        outcome=row.outcome,
        outcome_note=row.outcome_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_contribution(row: Row[Any]) -> ContributionSummary:
    """One row of the unified history, whatever kind of record it came from."""
    return ContributionSummary(
        id=row.id,
        contribution_type=row.contribution_type,
        label=row.label,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        destination_item_id=row.destination_item_id,
    )


def to_contribution_event(row: Row[Any]) -> ContributionEventEntry:
    """One appended timeline line."""
    return ContributionEventEntry(
        id=row.id,
        contribution_type=row.contribution_type,
        contribution_id=row.contribution_id,
        event_type=row.event_type,
        public_message=row.public_message,
        created_at=row.created_at,
    )


def to_review_task(row: Row[Any]) -> ReviewTaskSummary:
    """One queue entry. It names the item and the prediction, never the disputer."""
    return ReviewTaskSummary(
        id=row.id,
        content_item_id=row.content_item_id,
        prediction_id=row.prediction_id,
        task_type=row.task_type,
        reason=row.reason,
        priority=row.priority,
        status=row.status,
        assigned_to=row.assigned_to,
        claim_expires_at=row.claim_expires_at,
        created_at=row.created_at,
        completed_at=row.completed_at,
        title=row.title,
        permitted_excerpt=row.permitted_excerpt,
        canonical_url=row.canonical_url,
        platform=row.platform,
        relevance=row.relevance,
        stance=row.stance,
        hate_types=list(row.hate_types or ()),
        severity=row.severity,
        score=row.score,
        confidence_tier=row.confidence_tier,
        model_name=row.model_name,
        model_version=row.model_version,
    )


def to_review_decision(row: Row[Any]) -> ReviewDecisionEntry:
    """One appended decision."""
    return ReviewDecisionEntry(
        id=row.id,
        review_task_id=row.review_task_id,
        reviewer_id=row.reviewer_id,
        decision=row.decision,
        corrected_labels=row.corrected_labels,
        note=row.note,
        is_training_candidate=row.is_training_candidate,
        created_at=row.created_at,
    )


def to_insight(row: Row[Any]) -> InsightSummary:
    """One snapshot insight, counts and all."""
    return InsightSummary(
        id=row.id,
        author_id=row.user_id,
        author_display_name=row.author_display_name,
        title=row.title,
        claim=row.claim,
        metric=row.metric,
        numerator=row.numerator,
        denominator=row.denominator,
        window_start=row.window_start,
        window_end=row.window_end,
        figure_label=row.figure_label,
        filter_hash=row.filter_hash,
        explorer_href=row.explorer_href,
        source_keys=list(row.source_keys or ()),
        items_observed=row.items_observed,
        items_relevant=row.items_relevant,
        created_at=row.created_at,
    )


def to_capture(row: Row[Any]) -> CaptureSummary:
    """One first-party figure capture."""
    return CaptureSummary(
        id=row.id,
        alt_text=row.alt_text,
        image_source=row.image_source,
        filter_hash=row.filter_hash,
        explorer_href=row.explorer_href,
        created_at=row.created_at,
    )


def to_reaction_counts(row: Row[Any] | None) -> PostReactionCounts:
    """Counts on one note. A note nobody reacted to has no row and reads as zero."""
    if row is None:
        return PostReactionCounts()
    return PostReactionCounts(
        useful=row.useful_count or 0,
        needs_context=row.needs_context_count or 0,
        viewer=ReactionKind(row.viewer_reaction) if row.viewer_reaction else None,
    )


def to_discussion_post(
    row: Row[Any],
    *,
    capture: CaptureSummary | None,
    reactions: PostReactionCounts,
) -> DiscussionPostEntry:
    """One note in a thread. A retracted one keeps its place and loses its capture."""
    return DiscussionPostEntry(
        id=row.id,
        snapshot_insight_id=row.snapshot_insight_id,
        author_id=row.user_id,
        author_display_name=row.author_display_name,
        body=row.body,
        created_at=row.created_at,
        retracted_at=row.retracted_at,
        capture=capture,
        reactions=reactions,
    )


def to_viewer_post(
    row: Row[Any],
    *,
    capture: CaptureSummary | None,
    reactions: PostReactionCounts,
) -> ViewerPostEntry:
    """One of the caller's own notes, carrying its parent insight's title."""
    return ViewerPostEntry(
        id=row.id,
        snapshot_insight_id=row.snapshot_insight_id,
        author_id=row.user_id,
        author_display_name=row.author_display_name,
        body=row.body,
        created_at=row.created_at,
        retracted_at=row.retracted_at,
        capture=capture,
        reactions=reactions,
        insight_title=row.insight_title,
    )
