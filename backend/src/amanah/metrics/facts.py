"""Builds a fact bundle from stored deterministic figures (B-S15.4, B-S15.9).

Bridges the two halves of Milestone 4. Everything read here was computed in SQL
and stored; nothing is recounted, estimated, or inferred. The result is the entire
context the narrative layer and the assistant are permitted to see.

Strata are carried through as separate facts rather than summed. A caller asking
for "the rate" over a window that mixes enriched seeds with ordinary monitoring
gets a per-stratum breakdown plus the disclosure that explains why the two are not
one number, and the model is told in its prompt that it may not combine them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from amanah.api.schemas.filters import ItemFilters
from amanah.db.repositories.catalogue import SourceStatusRepository
from amanah.db.repositories.dashboard import DashboardRepository
from amanah.db.views import authenticated_metric_buckets
from amanah.domain.enums import DataMode, SamplingStratum
from amanah.metrics.dashboard import PRIMARY_METRIC_KEY, DashboardData, build_dashboard
from amanah.ml.fact_bundle import Fact, FactBundle, filter_hash
from amanah.ml.versions import FILTER_VERSION

#: Methodology sentences the narrative layer may rely on and cite. Short, stable,
#: and stored here rather than fetched, so an insight's grounding cannot change
#: underneath a snapshot that already cited it.
METHODOLOGY_NOTES = (
    "Items are collected from a monitored sample of configured sources, not a random draw.",
    "Labels are produced by an automated model; confidence tiers are provisional until "
    "calibrated against a reviewed holdout set.",
    "A missing bucket means no collection ran for that period. It is not a count of zero.",
    "Association between a news event and a metric movement is co-occurrence in the same "
    "window and is never evidence that one produced the other.",
)


def build_fact_bundle(
    session: Session,
    *,
    filters: ItemFilters,
    data_mode: DataMode,
    now: datetime | None = None,
    dashboard: DashboardData | None = None,
) -> FactBundle:
    """Assemble the citable figures for one filtered window.

    `dashboard` lets a caller that has already computed the figures pass them in.
    `/v1/dashboard` does exactly that: recomputing them here would double the
    query load on the hottest endpoint, and — worse — the two passes would run at
    slightly different moments, so a bundle could describe a window one item
    wider than the numbers printed beside it.
    """
    if dashboard is None:
        dashboard = build_dashboard(
            metrics_repository=DashboardRepository(session),
            sources_repository=SourceStatusRepository(session),
            filters=filters,
            data_mode=data_mode,
            now=now,
        )
    rate = dashboard.metrics.likely_anti_muslim_rate

    facts: list[Fact] = [
        Fact(
            fact_id="observed_count",
            label="Items observed in the monitored sample for this window and filter set",
            value=dashboard.metrics.observed_count,
            unit="items",
            window_start=rate.window_start,
            window_end=rate.window_end,
        ),
        Fact(
            fact_id="muslim_related_count",
            label="Observed items the model classified as Muslim-related",
            value=dashboard.metrics.muslim_related_count,
            unit="items",
            window_start=rate.window_start,
            window_end=rate.window_end,
        ),
        Fact(
            fact_id="likely_anti_muslim_count",
            label="Muslim-related items the model classified as likely anti-Muslim rhetoric",
            value=dashboard.metrics.likely_anti_muslim_count,
            unit="items",
            window_start=rate.window_start,
            window_end=rate.window_end,
        ),
        Fact(
            fact_id="reviewed_count",
            label="Items a human reviewer has confirmed or corrected",
            value=dashboard.metrics.reviewed_count,
            unit="items",
            window_start=rate.window_start,
            window_end=rate.window_end,
        ),
        Fact(
            fact_id=PRIMARY_METRIC_KEY,
            label=(
                "Share of Muslim-related items classified as likely anti-Muslim rhetoric, "
                "in the monitored sample"
            ),
            value=rate.value,
            unit="ratio",
            numerator=rate.numerator,
            denominator=rate.denominator,
            window_start=rate.window_start,
            window_end=rate.window_end,
            note=(
                "Null when no Muslim-related items match these filters: the rate then has "
                "no denominator and is a gap, not a zero."
            ),
        ),
        Fact(
            fact_id="coverage_score",
            label="Share of observed items that carry a completed classification",
            value=dashboard.coverage.coverage_score,
            unit="ratio",
            window_start=rate.window_start,
            window_end=rate.window_end,
        ),
        Fact(
            fact_id="trend_gap_count",
            label="Days in this window with no computed metric bucket",
            value=sum(1 for point in dashboard.trend.points if point.is_gap),
            unit="days",
            window_start=rate.window_start,
            window_end=rate.window_end,
            note="Each of these days is a collection gap, not an observed count of zero.",
        ),
    ]
    facts.extend(_stratum_facts(session, rate.window_start, rate.window_end))

    return FactBundle(
        filter_hash=filter_hash(filters),
        data_version=FILTER_VERSION,
        facts=tuple(facts),
        coverage_warnings=dashboard.warnings,
        methodology_notes=METHODOLOGY_NOTES,
        sampling_disclosures=_stratum_disclosures(session, rate.window_start, rate.window_end),
        generated_at=now,
    )


def _stratum_facts(
    session: Session, window_start: datetime, window_end: datetime
) -> tuple[Fact, ...]:
    """One rate fact per sampling stratum present in the window.

    Separate facts rather than one pooled figure, because an enriched sample and
    ordinary monitoring answer different questions and a summed rate would answer
    neither.
    """
    facts: list[Fact] = []
    for row in _stratum_rows(session, window_start, window_end):
        stratum = SamplingStratum(row.sampling_stratum)
        relevant = int(row.relevant_count)
        facts.append(
            Fact(
                fact_id=f"{PRIMARY_METRIC_KEY}.{stratum.value}",
                label=(
                    "Share of Muslim-related items classified as likely anti-Muslim "
                    f"rhetoric, within the {stratum.value.replace('_', ' ')} sample"
                ),
                value=(int(row.likely_hate_count) / relevant) if relevant else None,
                unit="ratio",
                numerator=int(row.likely_hate_count),
                denominator=relevant,
                window_start=window_start,
                window_end=window_end,
                sampling_stratum=stratum,
                note=(
                    "This stratum must not be combined with another to produce a single "
                    "rate; the samples were drawn for different reasons."
                ),
            )
        )
    return tuple(facts)


def _stratum_rows(
    session: Session, window_start: datetime, window_end: datetime
) -> tuple[Row[Any], ...]:
    table = authenticated_metric_buckets
    statement = (
        select(
            table.c.sampling_stratum,
            func.sum(table.c.relevant_count).label("relevant_count"),
            func.sum(table.c.likely_hate_count).label("likely_hate_count"),
        )
        .where(
            table.c.metric_key == PRIMARY_METRIC_KEY,
            table.c.bucket_start >= window_start,
            table.c.bucket_start <= window_end,
        )
        .group_by(table.c.sampling_stratum)
        .order_by(table.c.sampling_stratum.asc())
    )
    return tuple(session.execute(statement).all())


def _stratum_disclosures(
    session: Session, window_start: datetime, window_end: datetime
) -> tuple[str, ...]:
    """The stored disclosure of every stratum present, without repeats."""
    table = authenticated_metric_buckets
    statement = (
        select(table.c.sampling_disclosure)
        .where(
            table.c.metric_key == PRIMARY_METRIC_KEY,
            table.c.bucket_start >= window_start,
            table.c.bucket_start <= window_end,
        )
        .distinct()
        .order_by(table.c.sampling_disclosure.asc())
    )
    return tuple(str(value) for value in session.execute(statement).scalars())
