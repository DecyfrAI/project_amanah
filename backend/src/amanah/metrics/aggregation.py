"""Deterministic bucket computation (B-S15.1, B-S15.2, B-S15.3, B-S15.9).

Every count here is produced by SQL. Nothing in this module calls a model, and
the numbers it writes stay correct when the AI boundary is unavailable — which is
the whole reason the split exists (`spec.md` section 11.2, FR-INSIGHT-002).

The aggregation groups by `(source, sampling stratum, day)` and writes one bucket
per group. The stratum is not decoration: an enriched seed sample is drawn from
places chosen *because* hostile content was expected there, so pooling it with
ordinary monitoring produces a number that looks like a prevalence rate and is
not one. Keeping the strata in separate rows means a caller has to decide, in the
open, which sample they are describing.

A group with no observed items produces no row. `spec.md` section 9.4 requires a
missing bucket to render as a gap, and writing a zero would make "we did not
collect" indistinguishable from "we collected and found none".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlalchemy import Row, Select, Table, Text, and_, func, literal, select, true
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.analysis import Prediction
from amanah.db.models.content import ContentItem
from amanah.db.models.metrics import LIKELY_ANTI_MUSLIM_RATE_KEY, MetricBucket
from amanah.db.models.sources import SourceSeedEntry
from amanah.domain.enums import (
    InferenceStatus,
    MetricInterval,
    Relevance,
    ReviewState,
    SamplingStratum,
    Stance,
)
from amanah.ml.versions import FILTER_VERSION

logger = logging.getLogger(__name__)

#: Review states that mean a person actually looked. `pending_review` and
#: `disputed` are requests for review, not evidence of one.
REVIEWED_STATES = (ReviewState.confirmed, ReviewState.corrected)

#: Attached to every bucket. The sentence a reader needs in order to interpret
#: the counts correctly, stored with the row rather than added at render time so
#: an exported bucket cannot lose it.
STRATUM_DISCLOSURES: dict[SamplingStratum, str] = {
    SamplingStratum.enriched: (
        "This bucket covers a sample deliberately drawn from places where hostile content "
        "was expected. Its rate describes that sample only and is not a prevalence measure "
        "for any platform or population."
    ),
    SamplingStratum.boundary_control: (
        "This bucket covers control material selected to test for false positives. Its rate "
        "describes that control set only."
    ),
    SamplingStratum.ordinary_monitoring: (
        "This bucket covers routine monitoring of configured sources. It is a monitored "
        "sample, not a random draw, and its rate is not a prevalence measure for any "
        "platform or population."
    ),
}


@dataclass(frozen=True, slots=True)
class AggregationResult:
    """What one aggregation pass wrote."""

    buckets_written: int
    strata: tuple[SamplingStratum, ...]


class MetricAggregator:
    """Recomputes stored metric buckets from canonical content and predictions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def rebuild(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        interval: MetricInterval = MetricInterval.daily,
    ) -> AggregationResult:
        """Recompute every bucket whose day falls in the window.

        Idempotent by construction: each row is upserted on the documented
        identity, so re-running an ETL stage converges on the same numbers rather
        than doubling them.
        """
        rows = self._session.execute(self._counts_query(window_start, window_end, interval)).all()
        strata: set[SamplingStratum] = set()
        for row in rows:
            stratum = SamplingStratum(row.sampling_stratum)
            strata.add(stratum)
            self._upsert_bucket(row, stratum=stratum, interval=interval)

        logger.info(
            "metric buckets rebuilt",
            extra={"bucket_count": len(rows), "interval": interval.value},
        )
        return AggregationResult(buckets_written=len(rows), strata=tuple(sorted(strata)))

    def _counts_query(
        self, window_start: datetime, window_end: datetime, interval: MetricInterval
    ) -> Select[Any]:
        """Count observed, relevant, likely-hate, reviewed, and confirmed items.

        The join to predictions is a lateral pick of the newest *successful*
        execution, matching how `authenticated_items` resolves a current label.
        Counting every prediction row instead would count an item once per model
        version it has been through.

        `coverage_score` is the share of observed items that actually carry a
        successful prediction. It is what turns "three items, none hateful" into
        the honest "three items, one analysed" on the screen.
        """
        latest = (
            select(Prediction.relevance, Prediction.stance)
            .where(
                Prediction.content_item_id == ContentItem.id,
                Prediction.inference_status == InferenceStatus.succeeded,
            )
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
            .limit(1)
            .lateral("latest")
        )
        bucket_start = func.date_trunc(_TRUNC_UNIT[interval], ContentItem.observed_at)
        # An item collected without a seed entry is ordinary monitoring: it was
        # not drawn from a purposively selected place.
        #
        # Cast to text before the coalesce. Postgres will not match an enum
        # against an untyped literal in `COALESCE`, and comparing the two as text
        # is exactly as safe here: the value is parsed back into `SamplingStratum`
        # below, so an unknown label would still fail loudly.
        stratum = func.coalesce(
            sql_cast(SourceSeedEntry.sampling_stratum, Text),
            sql_cast(literal(SamplingStratum.ordinary_monitoring.value), Text),
        )

        return (
            select(
                ContentItem.source_id.label("source_id"),
                stratum.label("sampling_stratum"),
                bucket_start.label("bucket_start"),
                func.count().label("observed_count"),
                func.count()
                .filter(latest.c.relevance == Relevance.muslim_related)
                .label("relevant_count"),
                func.count()
                .filter(latest.c.stance == Stance.likely_anti_muslim)
                .label("likely_hate_count"),
                func.count()
                .filter(ContentItem.effective_review_state.in_(REVIEWED_STATES))
                .label("reviewed_count"),
                func.count()
                .filter(
                    and_(
                        ContentItem.effective_review_state == ReviewState.confirmed,
                        latest.c.stance == Stance.likely_anti_muslim,
                    )
                )
                .label("confirmed_count"),
                func.count().filter(latest.c.stance.is_not(None)).label("analysed_count"),
            )
            .select_from(ContentItem)
            .outerjoin(SourceSeedEntry, SourceSeedEntry.id == ContentItem.source_seed_entry_id)
            .outerjoin(latest, true())
            .where(
                ContentItem.observed_at >= window_start,
                ContentItem.observed_at <= window_end,
            )
            .group_by(ContentItem.source_id, stratum, bucket_start)
        )

    def _upsert_bucket(
        self, row: Row[Any], *, stratum: SamplingStratum, interval: MetricInterval
    ) -> None:
        """Write one bucket, converging on re-run rather than accumulating."""
        observed = int(row.observed_count)
        analysed = int(row.analysed_count)
        table = cast(Table, MetricBucket.__table__)
        values: dict[str, Any] = {
            "metric_key": LIKELY_ANTI_MUSLIM_RATE_KEY,
            "source_id": row.source_id,
            "sampling_stratum": stratum.value,
            "interval": interval.value,
            "bucket_start": row.bucket_start,
            "observed_count": observed,
            "relevant_count": int(row.relevant_count),
            "likely_hate_count": int(row.likely_hate_count),
            "reviewed_count": int(row.reviewed_count),
            "confirmed_count": int(row.confirmed_count),
            # Null rather than zero when nothing was observed: a coverage of
            # 0/0 reads as a failure rather than as an absence of data.
            "coverage_score": (analysed / observed) if observed else None,
            "coverage_warnings": _coverage_warnings(observed=observed, analysed=analysed),
            "filter_version": FILTER_VERSION,
            "sampling_disclosure": STRATUM_DISCLOSURES[stratum],
        }
        refreshable = {
            table.c[column]: values[column]
            for column in (
                "observed_count",
                "relevant_count",
                "likely_hate_count",
                "reviewed_count",
                "confirmed_count",
                "coverage_score",
                "coverage_warnings",
                "sampling_disclosure",
            )
        }
        statement: Any = (
            insert(table)
            .values(**values)
            .on_conflict_do_update(
                constraint="metric_buckets_key_source_stratum_interval_bucket_filter_unique",
                set_=refreshable,
            )
        )
        self._session.execute(statement)


#: `date_trunc` unit per stored interval.
_TRUNC_UNIT: dict[MetricInterval, str] = {
    MetricInterval.hourly: "hour",
    MetricInterval.daily: "day",
    MetricInterval.weekly: "week",
}


def _coverage_warnings(*, observed: int, analysed: int) -> list[str]:
    """Publishable sentences about what this bucket does not cover."""
    if observed and analysed < observed:
        return [
            f"{observed - analysed} of {observed} item(s) in this bucket have not been "
            "analysed; they are counted as observed but appear in no classification count."
        ]
    return []
