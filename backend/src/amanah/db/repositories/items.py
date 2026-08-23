"""Parameterized reads over the authenticated item projection.

Every filter value reaches the database as a bound parameter through the
expression language; no fragment of a query is built by formatting a string with
caller input. The repository returns rows, never response models: shaping the
`/v1` contract is the service layer's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Row, Select, Table, select
from sqlalchemy.orm import Session

from amanah.api.schemas.filters import ItemFilters, ItemSort
from amanah.db import pagination
from amanah.db.views import authenticated_items
from amanah.domain.enums import ContentKind

#: One row is read beyond the requested page so the response can say whether a
#: next page exists without a second count query.
_LOOKAHEAD = 1


@dataclass(frozen=True, slots=True)
class ItemPage:
    """One page of items plus the cursor that continues it."""

    rows: tuple[Row[Any], ...]
    next_cursor: str | None


def build_filter_conditions(table: Table, filters: ItemFilters) -> list[ColumnElement[bool]]:
    """Translate validated filters into bound SQL conditions.

    Only filters the caller actually supplied become conditions. An unsupported
    filter never reaches here: the request model rejects unknown fields at the
    boundary, so a query is never silently broadened.
    """
    conditions: list[ColumnElement[bool]] = []
    if filters.date_from is not None:
        conditions.append(table.c.observed_at >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(table.c.observed_at <= filters.date_to)
    if filters.content_kinds:
        conditions.append(table.c.content_kind.in_([k.value for k in filters.content_kinds]))
    if filters.platforms:
        conditions.append(table.c.platform.in_([p.value for p in filters.platforms]))
    # Dataset provenance is filtered separately from platform: a datapack row
    # publishes `not_applicable` as its platform while staying findable by the
    # dataset it came from.
    if filters.dataset_provider is not None:
        conditions.append(table.c.dataset_provider == filters.dataset_provider)
    if filters.dataset_name is not None:
        conditions.append(table.c.dataset_name == filters.dataset_name)
    if filters.dataset_version is not None:
        conditions.append(table.c.dataset_version == filters.dataset_version)
    if filters.country_codes:
        conditions.append(table.c.country_code.in_(list(filters.country_codes)))
    if filters.narrative_tags:
        conditions.append(table.c.narrative_tags.overlap(list(filters.narrative_tags)))
    if filters.severities:
        conditions.append(table.c.severity.in_([int(s) for s in filters.severities]))
    if filters.review_states:
        conditions.append(table.c.review_state.in_([r.value for r in filters.review_states]))
    if filters.confidence_tiers:
        conditions.append(table.c.confidence_tier.in_([c.value for c in filters.confidence_tiers]))
    return conditions


class ItemRepository:
    """Reads of the authenticated-safe item projection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_items(
        self,
        *,
        filters: ItemFilters,
        sort: ItemSort,
        limit: int,
        cursor: str | None = None,
        content_kinds: tuple[ContentKind, ...] | None = None,
    ) -> ItemPage:
        """Return one page of items in the requested total order.

        `content_kinds` is the route's own restriction — `/v1/news` reads
        articles only — applied on top of whatever the caller filtered.
        """
        table = authenticated_items
        statement = select(table)
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        if content_kinds:
            statement = statement.where(table.c.content_kind.in_([k.value for k in content_kinds]))
        if cursor is not None:
            key_value, row_id = pagination.decode_cursor(cursor, sort)
            statement = statement.where(pagination.keyset_predicate(table, sort, key_value, row_id))

        statement = statement.order_by(*pagination.order_by(table, sort)).limit(limit + _LOOKAHEAD)
        rows = tuple(self._session.execute(statement).all())

        if len(rows) <= limit:
            return ItemPage(rows=rows, next_cursor=None)
        page = rows[:limit]
        last = page[-1]
        key_value = _sort_key_of(last, sort)
        return ItemPage(rows=page, next_cursor=pagination.encode_cursor(sort, key_value, last.id))

    def get_item(self, item_id: UUID) -> Row[Any] | None:
        """Return one item, or `None` when it does not exist or is not visible.

        The projection already refuses rows to a session with no verified
        identity, so "not visible" and "absent" are the same answer here — and
        the route turns both into the same `404`.
        """
        statement: Select[Any] = select(authenticated_items).where(
            authenticated_items.c.id == item_id
        )
        return self._session.execute(statement).one_or_none()


def _sort_key_of(row: Row[Any], sort: ItemSort) -> pagination.SortKey:
    """The value the cursor must carry for this sort, with nulls substituted."""
    order = pagination.SORT_ORDERS[sort]
    value: pagination.SortKey | None = getattr(row, order.column)
    if value is None:
        # Every sort with a nullable key defines a substitute, so this is
        # reachable only for those sorts.
        assert order.null_substitute is not None  # noqa: S101 - invariant of SORT_ORDERS
        return order.null_substitute
    return value
