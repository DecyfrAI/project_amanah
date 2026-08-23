"""Keyset (cursor) pagination for the authenticated collections.

`OFFSET` is not used: it scans and discards rows, and it drops or repeats rows
when the underlying data changes between pages. Every sort here pairs its
primary key expression with the row's `id`, so the ordering is total and a page
boundary is unambiguous even when many rows share a timestamp or a score.

A cursor is opaque to clients but not trusted by the server: it is decoded,
validated, and rejected if it was issued for a different sort.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Table, func, literal, tuple_

from amanah.api.schemas.filters import ItemSort

#: A sort key is a timestamp or a number. Nulls never reach a cursor: every
#: sort substitutes a value that keeps unclassified rows at the end.
type SortKey = datetime | float


class InvalidCursorError(ValueError):
    """The cursor was malformed, or was issued for a different sort order."""


@dataclass(frozen=True, slots=True)
class SortOrder:
    """How one documented sort maps onto a total ordering.

    `null_substitute` keeps rows with no prediction at the end of the list under
    every sort. Substituting rather than relying on `NULLS LAST` is what lets the
    page boundary stay a single row comparison.
    """

    column: str
    descending: bool
    null_substitute: float | None = None


#: `spec.md` section 9.3. Adding a sort means adding a row here; a value that is
#: not in this table is rejected at the boundary as an unsupported sort.
SORT_ORDERS: dict[ItemSort, SortOrder] = {
    ItemSort.newest: SortOrder(column="observed_at", descending=True),
    ItemSort.oldest: SortOrder(column="observed_at", descending=False),
    # An unclassified item has no score. Under "highest first" it sorts below
    # every real score; under "lowest first" it sorts above every real one.
    ItemSort.highest_confidence: SortOrder(column="score", descending=True, null_substitute=-1.0),
    ItemSort.lowest_confidence: SortOrder(column="score", descending=False, null_substitute=2.0),
    ItemSort.highest_severity: SortOrder(column="severity", descending=True, null_substitute=-1.0),
}


def sort_key_expression(table: Table, sort: ItemSort) -> ColumnElement[Any]:
    """The primary ordering expression for one sort."""
    order = SORT_ORDERS[sort]
    column = table.c[order.column]
    if order.null_substitute is None:
        return column
    return func.coalesce(column, order.null_substitute)


def order_by(table: Table, sort: ItemSort) -> list[ColumnElement[Any]]:
    """The full, total ordering: the sort key then the row identifier."""
    order = SORT_ORDERS[sort]
    key = sort_key_expression(table, sort)
    identifier = table.c.id
    if order.descending:
        return [key.desc(), identifier.desc()]
    return [key.asc(), identifier.asc()]


def encode_cursor(sort: ItemSort, key_value: SortKey, row_id: UUID) -> str:
    """Serialize the last row of a page into an opaque cursor."""
    payload = {
        "sort": sort.value,
        "key": _encode_key(key_value),
        "id": str(row_id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str, sort: ItemSort) -> tuple[SortKey, UUID]:
    """Recover the page boundary, or reject the cursor.

    A cursor carries the sort it was issued for. Reusing one after changing the
    sort would silently produce a page from the wrong ordering, so it is refused
    instead.
    """
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
    except (ValueError, binascii.Error) as exc:
        raise InvalidCursorError("cursor is not readable") from exc

    if not isinstance(payload, dict) or payload.get("sort") != sort.value:
        raise InvalidCursorError("cursor was issued for a different sort order")
    try:
        row_id = UUID(str(payload["id"]))
        key_value = _decode_key(payload["key"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidCursorError("cursor is incomplete") from exc
    return key_value, row_id


def keyset_predicate(
    table: Table, sort: ItemSort, key_value: SortKey, row_id: UUID
) -> ColumnElement[bool]:
    """Rows strictly after the cursor position in the sort's total ordering."""
    order = SORT_ORDERS[sort]
    boundary = tuple_(sort_key_expression(table, sort), table.c.id)
    # Bound parameters, not inlined values: a cursor is caller-supplied input.
    position = tuple_(literal(key_value), literal(row_id))
    return boundary < position if order.descending else boundary > position


def _encode_key(value: SortKey) -> dict[str, object]:
    """Represent a sort key as JSON without losing timestamp precision."""
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.astimezone(UTC).isoformat()}
    return {"type": "scalar", "value": value}


def _decode_key(encoded: object) -> SortKey:
    if not isinstance(encoded, dict):
        raise ValueError("cursor key is malformed")
    if encoded.get("type") == "datetime":
        return datetime.fromisoformat(str(encoded["value"]))
    if encoded.get("type") == "scalar":
        return float(encoded["value"])
    raise ValueError("cursor key is malformed")
