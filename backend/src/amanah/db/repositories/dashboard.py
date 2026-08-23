"""Deterministic dashboard aggregates.

Every number the dashboard shows is counted here in SQL. Nothing is estimated,
and a window with no data yields an absent bucket rather than a zero, so a gap
stays visibly a gap all the way to the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from amanah.api.schemas.filters import ItemFilters
from amanah.db.repositories.items import build_filter_conditions
from amanah.db.views import authenticated_items, authenticated_metric_buckets
from amanah.domain.enums import ContentKind, MetricInterval, Relevance, ReviewState, Stance

#: Review states that mean a human has actually looked at the item. `disputed`
#: and `pending_review` are requests for review, not evidence of one.
REVIEWED_STATES = (ReviewState.confirmed.value, ReviewState.corrected.value)


@dataclass(frozen=True, slots=True)
class ObservedCounts:
    """The counts every dashboard rate is derived from.

    They nest: `likely_anti_muslim` is a subset of `muslim_related`, which is a
    subset of `observed`. Publishing all three is what stops the rate from being
    read as a measure of anything wider than the monitored sample.
    """

    observed: int
    muslim_related: int
    likely_anti_muslim: int
    reviewed: int


class DashboardRepository:
    """Aggregates and headline reads over the authenticated item projection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_items(self, filters: ItemFilters) -> ObservedCounts:
        """Count observed, Muslim-related, likely anti-Muslim, and reviewed items."""
        table = authenticated_items
        statement = select(
            func.count().label("observed"),
            func.count()
            .filter(table.c.relevance == Relevance.muslim_related.value)
            .label("muslim_related"),
            func.count()
            .filter(table.c.stance == Stance.likely_anti_muslim.value)
            .label("likely_anti_muslim"),
            func.count().filter(table.c.review_state.in_(REVIEWED_STATES)).label("reviewed"),
        )
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        row = self._session.execute(statement).one()
        return ObservedCounts(
            observed=row.observed,
            muslim_related=row.muslim_related,
            likely_anti_muslim=row.likely_anti_muslim,
            reviewed=row.reviewed,
        )

    def count_items_in_window(
        self, filters: ItemFilters, window_start: datetime, window_end: datetime
    ) -> ObservedCounts:
        """Count over an explicit window, ignoring the filters' own dates.

        Used for the preceding comparison window, so a change figure is computed
        from the same filters over the same span rather than from a guess.
        """
        shifted = filters.model_copy(update={"date_from": window_start, "date_to": window_end})
        return self.count_items(shifted)

    def read_headlines(self, filters: ItemFilters, limit: int) -> tuple[Row[Any], ...]:
        """Return the newest Muslim-related news articles under these filters.

        An article whose relevance has not been established is deliberately
        excluded: presenting an unclassified item as a relevant headline would
        claim something the data does not support.
        """
        table = authenticated_items
        statement = select(table).where(
            table.c.content_kind == ContentKind.news_article.value,
            table.c.relevance == Relevance.muslim_related.value,
            table.c.published_at.is_not(None),
        )
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        statement = statement.order_by(table.c.published_at.desc(), table.c.id.desc()).limit(limit)
        return tuple(self._session.execute(statement).all())

    def read_metric_buckets(
        self,
        *,
        metric_key: str,
        interval: MetricInterval,
        window_start: datetime,
        window_end: datetime,
    ) -> tuple[Row[Any], ...]:
        """Return stored buckets in the window, oldest first.

        Buckets that were never computed are simply not returned; the service
        turns each missing position into an explicit gap rather than a zero.
        """
        table = authenticated_metric_buckets
        statement = (
            select(
                table.c.bucket_start,
                func.sum(table.c.observed_count).label("observed_count"),
                func.sum(table.c.relevant_count).label("relevant_count"),
                func.sum(table.c.likely_hate_count).label("likely_hate_count"),
                func.sum(table.c.reviewed_count).label("reviewed_count"),
                func.min(table.c.coverage_score).label("coverage_score"),
            )
            .where(
                table.c.metric_key == metric_key,
                table.c.interval == interval.value,
                table.c.bucket_start >= window_start,
                table.c.bucket_start <= window_end,
            )
            .group_by(table.c.bucket_start)
            .order_by(table.c.bucket_start.asc())
        )
        return tuple(self._session.execute(statement).all())

    def observed_window(self, filters: ItemFilters) -> tuple[datetime | None, datetime | None]:
        """The earliest and latest observation actually present under the filters.

        A rate must state the window it covers. When the caller supplied no
        dates, the honest window is the one the data itself spans.
        """
        table = authenticated_items
        statement = select(
            func.min(table.c.observed_at).label("earliest"),
            func.max(table.c.observed_at).label("latest"),
        )
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        row = self._session.execute(statement).one()
        return row.earliest, row.latest

    def source_scope(self, filters: ItemFilters) -> tuple[str, ...]:
        """The sources the denominator was actually drawn from.

        A rate must name its scope. Reporting the sources present under the
        filters is what stops "the monitored sample" from being an unfalsifiable
        phrase.
        """
        table = authenticated_items
        statement = select(table.c.source_name).distinct().order_by(table.c.source_name.asc())
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        return tuple(str(name) for name in self._session.execute(statement).scalars())

    def count_unclassified(self, filters: ItemFilters) -> int:
        """Items with no successful prediction yet.

        Surfaced as a partial-coverage warning: they are in the denominator of
        `observed` but cannot be in any classification count.
        """
        table = authenticated_items
        statement = select(func.count()).where(table.c.prediction_id.is_(None))
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        return int(self._session.execute(statement).scalar_one())
