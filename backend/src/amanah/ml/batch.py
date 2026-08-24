"""Batch classification and aggregation over canonical content (B-S14, B-S15).

The step between collection and the dashboard: classify what has arrived, then
recompute the deterministic buckets over it. Both halves are idempotent, so an
interrupted invocation is resumed by the next one rather than restarted.

Ordering matters and is not incidental. Classification runs first because
aggregation counts predictions; running them the other way would produce buckets
that describe the previous run's labels. Aggregation runs even when every
classification deferred, because the observed counts and the coverage score are
still true and the dashboard needs them (`spec.md` FR-INSIGHT-007).

Classification stops early when the budget is spent. Continuing would issue one
refused call per remaining item, and each of those would write a `deferred`
prediction row that the next run has to skip past.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Row, func, or_, select, true
from sqlalchemy.orm import Session

from amanah.db.models.analysis import Prediction
from amanah.db.models.content import ContentItem
from amanah.db.models.sources import Source
from amanah.domain.enums import InferenceStatus, MetricInterval
from amanah.metrics.aggregation import AggregationResult, MetricAggregator
from amanah.ml.classification import (
    ClassifiableItem,
    ClassificationService,
    build_model_input,
    transfer_for,
)

logger = logging.getLogger(__name__)

#: Items classified in one invocation. A bound rather than a preference: the run
#: has a token budget, and a batch larger than the budget can pay for only
#: produces deferrals.
DEFAULT_BATCH_SIZE = 200

#: Statuses worth attempting again on a later run. A policy block will not change
#: under the same policy, and an invalid output is already with a reviewer.
_RETRYABLE_STATUSES = (InferenceStatus.deferred, InferenceStatus.provider_failure)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """What one analysis pass did."""

    classified: int
    deferred: int
    aggregation: AggregationResult


def analyze(
    session: Session,
    *,
    classifier: ClassificationService,
    window_start: datetime,
    window_end: datetime,
    batch_size: int = DEFAULT_BATCH_SIZE,
    interval: MetricInterval = MetricInterval.daily,
) -> AnalysisResult:
    """Classify pending items in the window, then rebuild the buckets over them."""
    classified = 0
    deferred = 0

    for row in _pending(session, window_start, window_end, batch_size):
        record = classifier.classify(_to_classifiable(row))
        if record.status is InferenceStatus.succeeded:
            classified += 1
            continue
        deferred += 1
        if record.status is InferenceStatus.deferred:
            # The budget is spent, or the provider is refusing. Every further
            # item in this batch would defer too.
            logger.info("classification stopped early", extra={"reason": "inference_deferred"})
            break

    aggregation = MetricAggregator(session).rebuild(
        window_start=window_start, window_end=window_end, interval=interval
    )
    logger.info(
        "analysis pass complete",
        extra={
            "classified": classified,
            "deferred": deferred,
            "buckets_written": aggregation.buckets_written,
        },
    )
    return AnalysisResult(classified=classified, deferred=deferred, aggregation=aggregation)


def _pending(
    session: Session, window_start: datetime, window_end: datetime, limit: int
) -> tuple[Row[Any], ...]:
    """Items in the window with no usable prediction yet.

    An item whose newest prediction succeeded is done. One whose newest attempt
    deferred or hit a provider failure comes back; one that was policy-blocked or
    produced invalid output does not, because neither resolves by trying again.

    Ordered oldest first so a backlog is worked through in the order it arrived
    rather than newest-first, which would starve the oldest items indefinitely.
    """
    latest = (
        select(Prediction.inference_status)
        .where(Prediction.content_item_id == ContentItem.id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(1)
        .lateral("latest")
    )
    statement = (
        select(
            ContentItem.id,
            ContentItem.content_hash,
            ContentItem.normalized_text,
            ContentItem.normalized_context,
            ContentItem.permitted_excerpt,
            ContentItem.is_fixture,
            Source.platform,
            Source.retention_policy,
        )
        .select_from(ContentItem)
        .join(Source, Source.id == ContentItem.source_id)
        .outerjoin(latest, true())
        .where(
            ContentItem.observed_at >= window_start,
            ContentItem.observed_at <= window_end,
            # Something to classify. An item with no text at all would be sent as
            # an empty prompt and labelled on nothing.
            func.coalesce(ContentItem.normalized_text, ContentItem.permitted_excerpt).is_not(None),
            # Never attempted, or attempted and left in a state a later run can
            # still resolve.
            or_(
                latest.c.inference_status.is_(None),
                latest.c.inference_status.in_(_RETRYABLE_STATUSES),
            ),
        )
        .order_by(ContentItem.observed_at.asc(), ContentItem.id.asc())
        .limit(limit)
    )
    return tuple(session.execute(statement).all())


def _to_classifiable(row: Row[Any]) -> ClassifiableItem:
    """Assemble one item's model input and its transfer provenance.

    An item whose licence permitted only an excerpt is a different data class
    from one whose full text was permitted, so which field supplied the text
    decides how the transfer gate treats it.
    """
    return ClassifiableItem(
        content_item_id=row.id,
        content_hash=row.content_hash,
        model_text=build_model_input(
            normalized_text=row.normalized_text or row.permitted_excerpt,
            context=dict(row.normalized_context or {}),
        ),
        transfer=transfer_for(
            platform=row.platform,
            retention_policy=row.retention_policy,
            is_fixture=bool(row.is_fixture),
            has_permitted_excerpt_only=not row.normalized_text,
        ),
    )
