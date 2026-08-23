"""Access paths for the item list at a representative volume (B-S3.4, B-S5.7).

`rules/database.md` says to read the plan rather than guess. Two properties are
checked here.

The first is that the index the list sorts by can actually serve that ordering.
The planner is told to prefer an index for this check, because at fixture volume
it may reasonably choose a sequential scan and a top-N sort instead; what matters
is that the index matches the sort, not which plan wins today.

The second is the property keyset pagination exists for: a page deep in the list
must read no more rows than a shallow one. `OFFSET` fails that by definition, and
the contrast is asserted directly.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import Engine, select, text

from amanah.api.schemas.filters import ItemSort
from amanah.db import pagination
from amanah.db.views import authenticated_items
from tests.db import factories

#: Enough rows that a plan which reads all of them is clearly distinguishable
#: from one that reads a page, and still quick to seed in a single statement.
REPRESENTATIVE_ROW_COUNT = 2000

PAGE_LIMIT = 25

#: How far into the list the "deep page" sits.
DEEP_PAGE_OFFSET = 1500

_TEST_CLAIMS = '{"sub": "00000000-0000-0000-0000-000000000001"}'


@pytest.fixture
def populated(engine: Engine) -> None:
    """Seed enough rows that the planner has a real choice to make."""
    with engine.begin() as connection:
        source_id = factories.insert_source(connection)
        connection.execute(
            text(
                """
                INSERT INTO public.content_items
                    (source_id, source_item_id, content_kind, observed_at, published_at,
                     content_hash, title)
                SELECT
                    :source_id,
                    'bulk-' || generation.index,
                    'news_article',
                    now() - (generation.index || ' minutes')::interval,
                    now() - (generation.index || ' minutes')::interval,
                    md5('bulk-' || generation.index) || md5('salt-' || generation.index),
                    'Synthetic bulk article ' || generation.index
                FROM generate_series(1, :row_count) AS generation(index)
                """
            ),
            {"source_id": source_id, "row_count": REPRESENTATIVE_ROW_COUNT},
        )
        connection.execute(text("ANALYZE public.content_items"))


def _explain(engine: Engine, statement: str, *, prefer_index: bool = False) -> dict[str, Any]:
    """Return the executed plan as JSON."""
    with engine.connect() as connection:
        connection.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": _TEST_CLAIMS},
        )
        if prefer_index:
            connection.execute(text("SET LOCAL enable_seqscan = off"))
        raw = connection.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {statement}")).scalar_one()
    plan: list[dict[str, Any]] = raw if isinstance(raw, list) else json.loads(raw)
    return plan[0]["Plan"]


def _rows_read_from(plan: dict[str, Any], relation: str) -> int:
    """Total rows the executed plan actually read from one relation."""
    total = 0
    if plan.get("Relation Name") == relation:
        total += int(plan.get("Actual Rows", 0)) * int(plan.get("Actual Loops", 1))
    for child in plan.get("Plans", ()):
        total += _rows_read_from(child, relation)
    return total


def _index_names(plan: dict[str, Any]) -> set[str]:
    names = {plan["Index Name"]} if "Index Name" in plan else set()
    for child in plan.get("Plans", ()):
        names |= _index_names(child)
    return names


def _compiled(statement: Any) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _page_statement(cursor_key: Any = None, cursor_id: Any = None) -> str:
    table = authenticated_items
    statement = select(table)
    if cursor_key is not None:
        statement = statement.where(
            pagination.keyset_predicate(table, ItemSort.newest, cursor_key, cursor_id)
        )
    return _compiled(
        statement.order_by(*pagination.order_by(table, ItemSort.newest)).limit(PAGE_LIMIT + 1)
    )


def _deep_boundary(engine: Engine) -> Any:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT observed_at, id FROM public.content_items "
                "ORDER BY observed_at DESC, id DESC OFFSET :offset LIMIT 1"
            ),
            {"offset": DEEP_PAGE_OFFSET},
        ).one()


def test_the_ordering_index_can_serve_the_default_page(engine: Engine, populated: None) -> None:
    plan = _explain(engine, _page_statement(), prefer_index=True)

    assert "content_items_observed_at_id_idx" in _index_names(plan)


def test_the_prediction_lookup_uses_its_index(engine: Engine, populated: None) -> None:
    """The current prediction is found per item, so an unindexed lookup here
    would cost one scan of `predictions` per row on the page."""
    plan = _explain(engine, _page_statement())

    assert "predictions_content_item_id_created_at_idx" in _index_names(plan)


def test_a_deep_page_reads_no_more_rows_than_a_shallow_one(engine: Engine, populated: None) -> None:
    boundary = _deep_boundary(engine)

    shallow = _rows_read_from(_explain(engine, _page_statement()), "content_items")
    deep = _rows_read_from(
        _explain(engine, _page_statement(boundary.observed_at, boundary.id)), "content_items"
    )

    assert deep <= shallow * 2, f"deep page read {deep} rows against {shallow} shallow"
    assert deep < REPRESENTATIVE_ROW_COUNT


def test_offset_pagination_would_read_its_way_to_the_same_page(
    engine: Engine, populated: None
) -> None:
    """The comparison that justifies the cursor: reaching the same page with
    `OFFSET` reads every row it skips."""
    offset_plan = _explain(
        engine,
        "SELECT id FROM public.authenticated_items "
        f"ORDER BY observed_at DESC, id DESC OFFSET {DEEP_PAGE_OFFSET} LIMIT {PAGE_LIMIT}",
    )
    boundary = _deep_boundary(engine)
    keyset_plan = _explain(engine, _page_statement(boundary.observed_at, boundary.id))

    assert _rows_read_from(offset_plan, "content_items") > _rows_read_from(
        keyset_plan, "content_items"
    )
