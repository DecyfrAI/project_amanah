"""Translation from projection rows into the published `/v1` models.

One place builds an item response. Adding a column to a projection therefore
does not leak it: it has to be named here first, and every route shares this
mapping so the item on a list, on a headline card, and on the detail page cannot
disagree about what an item is.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Row

from amanah.api.schemas.connections import ConnectionState
from amanah.api.schemas.dashboard import HeadlineCard
from amanah.api.schemas.items import DatasetProvenance, ItemDetail, ItemSummary
from amanah.api.schemas.resources import ResourceEntry

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
