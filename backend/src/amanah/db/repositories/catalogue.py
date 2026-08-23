"""Reads of the curated catalogue, connector state, and allowed filter values.

Each of these is a small read over one authenticated-safe projection, so they
share a module rather than three near-empty ones.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from amanah.db.views import (
    authenticated_items,
    authenticated_resources,
    authenticated_source_status,
)
from amanah.domain.enums import ResourceCategory


class ResourceRepository:
    """Reviewed education resources.

    The projection contains published entries only, so there is no draft state to
    filter out and no way for this repository to return one by mistake.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_resources(
        self,
        *,
        category: ResourceCategory | None = None,
        country_scope: str | None = None,
    ) -> tuple[Row[Any], ...]:
        table = authenticated_resources
        statement = select(table)
        if category is not None:
            statement = statement.where(table.c.category == category.value)
        if country_scope is not None:
            statement = statement.where(table.c.country_scope == country_scope)
        statement = statement.order_by(table.c.category.asc(), table.c.title.asc())
        return tuple(self._session.execute(statement).all())


class SourceStatusRepository:
    """Connector coverage and freshness.

    The projection carries no key, connection string, host, or provider error
    body, so a connector-state response cannot leak one.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sources(self) -> tuple[Row[Any], ...]:
        table = authenticated_source_status
        statement = select(table).order_by(table.c.name.asc())
        return tuple(self._session.execute(statement).all())

    def latest_success_at(self) -> datetime | None:
        """The most recent successful collection across all sources."""
        table = authenticated_source_status
        latest = self._session.execute(select(func.max(table.c.last_success_at))).scalar_one()
        return latest if isinstance(latest, datetime) else None


class FilterValueRepository:
    """The filter values that actually exist in the data.

    Offering a value the data cannot produce would invite an empty result that
    looks like a finding, so every list here is derived from stored rows.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def _distinct(self, column_name: str) -> tuple[str, ...]:
        column = authenticated_items.c[column_name]
        statement = select(column).where(column.is_not(None)).distinct().order_by(column.asc())
        return tuple(str(value) for value in self._session.execute(statement).scalars())

    def platforms(self) -> tuple[str, ...]:
        return self._distinct("platform")

    def content_kinds(self) -> tuple[str, ...]:
        return self._distinct("content_kind")

    def country_codes(self) -> tuple[str, ...]:
        return self._distinct("country_code")

    def narrative_tags(self) -> tuple[str, ...]:
        """Distinct tags across every item's tag array.

        Expanded in a subquery rather than a set-returning function in the outer
        select list, so `DISTINCT` and `ORDER BY` apply to the expanded rows.
        """
        expanded = select(func.unnest(authenticated_items.c.narrative_tags).label("tag")).subquery()
        statement = select(expanded.c.tag).distinct().order_by(expanded.c.tag.asc())
        return tuple(str(value) for value in self._session.execute(statement).scalars())

    def datasets(self) -> tuple[Row[Any], ...]:
        """Provider, name, and version of every dataset present in the data.

        Returned separately from platforms: a datapack row publishes `N/A` as its
        platform, and that display value must never erase its dataset lineage.
        """
        table = authenticated_items
        statement = (
            select(table.c.dataset_provider, table.c.dataset_name, table.c.dataset_version)
            .where(table.c.dataset_provider.is_not(None))
            .distinct()
            .order_by(
                table.c.dataset_provider.asc(),
                table.c.dataset_name.asc(),
                table.c.dataset_version.asc(),
            )
        )
        return tuple(self._session.execute(statement).all())
