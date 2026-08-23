"""Assembles the authenticated dashboard from deterministic counts.

Three rules shape everything here.

* A rate never travels alone. It carries its numerator, denominator, window,
  source scope, coverage, and data mode, so it cannot be quoted as a bare
  percentage.
* Missing data is a gap. A day with no computed bucket is returned as a gap with
  null counts; it is never rendered as zero, because "we did not collect" and
  "we collected and found none" are different claims.
* Nothing is inferred. Every number is counted in SQL; the narrative layer that
  explains these facts arrives later and may only cite them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from amanah.api.schemas.common import CoverageSummary, MetricRate
from amanah.api.schemas.dashboard import (
    DashboardMetrics,
    DashboardTrend,
    HeadlineCard,
    TrendPoint,
)
from amanah.api.schemas.filters import ItemFilters
from amanah.api.v1.mappers import to_headline_card
from amanah.db.repositories.catalogue import SourceStatusRepository
from amanah.db.repositories.dashboard import DashboardRepository, ObservedCounts
from amanah.domain.enums import DataMode, MetricInterval

#: `spec.md` section 9.5: `likely_anti_muslim_items / muslim_related_items`, in
#: the monitored sample.
PRIMARY_METRIC_KEY = "likely_anti_muslim_rate"

#: How many headline cards the dashboard leads with.
HEADLINE_LIMIT = 6

#: Window used when the caller supplied no dates and the store is empty, so the
#: response still states a window rather than an open-ended one.
DEFAULT_WINDOW = timedelta(days=30)

#: Collection older than this is reported as stale. The dashboard keeps showing
#: the last successful data and says it is stale; it never silently substitutes
#: fixtures or represents the gap as zero.
STALE_AFTER = timedelta(hours=24)

#: A trend bucket is a day. Longer windows still return one point per day so a
#: gap stays visible instead of being averaged away.
TREND_INTERVAL = MetricInterval.daily


@dataclass(frozen=True, slots=True)
class DashboardData:
    """Everything `GET /v1/dashboard` returns, before the envelope is added."""

    coverage: CoverageSummary
    metrics: DashboardMetrics
    trend: DashboardTrend
    headlines: tuple[HeadlineCard, ...]
    warnings: tuple[str, ...]
    is_stale: bool


def build_dashboard(
    *,
    metrics_repository: DashboardRepository,
    sources_repository: SourceStatusRepository,
    filters: ItemFilters,
    data_mode: DataMode,
    now: datetime | None = None,
) -> DashboardData:
    """Count, assemble, and disclose."""
    moment = now or datetime.now(UTC)
    window_start, window_end = _resolve_window(metrics_repository, filters, moment)

    counts = metrics_repository.count_items(filters)
    scope = metrics_repository.source_scope(filters)
    unclassified = metrics_repository.count_unclassified(filters)
    last_success_at = sources_repository.latest_success_at()

    rate = MetricRate(
        numerator=counts.likely_anti_muslim,
        denominator=counts.muslim_related,
        window_start=window_start,
        window_end=window_end,
        source_scope=list(scope),
        coverage_score=_coverage_score(counts, unclassified),
        data_mode=data_mode,
    )
    trend, gap_count = _build_trend(metrics_repository, window_start, window_end)
    is_stale = _is_stale(last_success_at, moment)
    warnings = _warnings(
        counts=counts,
        unclassified=unclassified,
        gap_count=gap_count,
        last_success_at=last_success_at,
        is_stale=is_stale,
        sources_repository=sources_repository,
    )

    return DashboardData(
        coverage=CoverageSummary(
            last_success_at=last_success_at,
            coverage_score=_coverage_score(counts, unclassified),
            data_mode=data_mode,
            is_stale=is_stale,
            warnings=list(warnings),
        ),
        metrics=DashboardMetrics(
            observed_count=counts.observed,
            muslim_related_count=counts.muslim_related,
            likely_anti_muslim_count=counts.likely_anti_muslim,
            reviewed_count=counts.reviewed,
            likely_anti_muslim_rate=rate,
            rate_change=_rate_change(metrics_repository, filters, window_start, window_end, rate),
        ),
        trend=trend,
        headlines=tuple(
            to_headline_card(row)
            for row in metrics_repository.read_headlines(filters, HEADLINE_LIMIT)
        ),
        warnings=warnings,
        is_stale=is_stale,
    )


def _resolve_window(
    repository: DashboardRepository, filters: ItemFilters, moment: datetime
) -> tuple[datetime, datetime]:
    """The window the metrics actually cover.

    When the caller named one, that is the answer. Otherwise the honest window is
    the span the data itself occupies, and an empty store falls back to a stated
    default rather than claiming to cover all of time.
    """
    if filters.date_from is not None and filters.date_to is not None:
        return filters.date_from, filters.date_to
    earliest, latest = repository.observed_window(filters)
    start = filters.date_from or earliest or moment - DEFAULT_WINDOW
    end = filters.date_to or latest or moment
    return (start, end) if start <= end else (end, start)


def _coverage_score(counts: ObservedCounts, unclassified: int) -> float | None:
    """Share of observed items that have actually been analysed.

    `None` when nothing was observed: a coverage of zero over zero items would
    read as a failure rather than as an absence of data.
    """
    if counts.observed == 0:
        return None
    return (counts.observed - unclassified) / counts.observed


def _rate_change(
    repository: DashboardRepository,
    filters: ItemFilters,
    window_start: datetime,
    window_end: datetime,
    current: MetricRate,
) -> float | None:
    """Change against the immediately preceding window of the same length.

    `None` whenever the comparison would be meaningless — no history, or no
    Muslim-related items to divide by — rather than a fabricated zero.
    """
    if current.value is None:
        return None
    span = window_end - window_start
    if span <= timedelta(0):
        return None
    previous = repository.count_items_in_window(filters, window_start - span, window_start)
    if previous.muslim_related == 0:
        return None
    return current.value - (previous.likely_anti_muslim / previous.muslim_related)


def _build_trend(
    repository: DashboardRepository, window_start: datetime, window_end: datetime
) -> tuple[DashboardTrend, int]:
    """One point per day, with every uncomputed day marked as a gap."""
    stored = {
        row.bucket_start.astimezone(UTC).date(): row
        for row in repository.read_metric_buckets(
            metric_key=PRIMARY_METRIC_KEY,
            interval=TREND_INTERVAL,
            window_start=window_start,
            window_end=window_end,
        )
    }

    points: list[TrendPoint] = []
    gaps = 0
    cursor = window_start.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    final = window_end.astimezone(UTC)
    while cursor <= final:
        row = stored.get(cursor.date())
        if row is None:
            gaps += 1
            points.append(TrendPoint(bucket_start=cursor, is_gap=True))
        else:
            points.append(
                TrendPoint(
                    bucket_start=cursor,
                    is_gap=False,
                    observed_count=int(row.observed_count),
                    muslim_related_count=int(row.relevant_count),
                    likely_anti_muslim_count=int(row.likely_hate_count),
                    coverage_score=row.coverage_score,
                )
            )
        cursor += timedelta(days=1)
    return DashboardTrend(interval=TREND_INTERVAL, points=points), gaps


def _is_stale(last_success_at: datetime | None, moment: datetime) -> bool:
    if last_success_at is None:
        return True
    return moment - last_success_at.astimezone(UTC) > STALE_AFTER


def _warnings(
    *,
    counts: ObservedCounts,
    unclassified: int,
    gap_count: int,
    last_success_at: datetime | None,
    is_stale: bool,
    sources_repository: SourceStatusRepository,
) -> tuple[str, ...]:
    """Publishable coverage warnings. Never a provider error body."""
    warnings: list[str] = []
    if last_success_at is None:
        warnings.append("No collection run has recorded a success yet.")
    elif is_stale:
        warnings.append(
            "Collection has not succeeded recently; the figures below are the last "
            "successful data, not current data."
        )
    if counts.observed == 0:
        warnings.append("No items match these filters, so no rate can be reported.")
    elif counts.muslim_related == 0:
        warnings.append(
            "No Muslim-related items match these filters, so the rate has no denominator."
        )
    if unclassified:
        warnings.append(
            f"{unclassified} item(s) in this window have not been analysed yet. They are "
            "counted as observed but cannot appear in any classification count."
        )
    if gap_count:
        warnings.append(f"Trend data is missing for {gap_count} day(s) in this window.")
    warnings.extend(
        row.safe_warning for row in sources_repository.list_sources() if row.safe_warning
    )
    return tuple(warnings)
