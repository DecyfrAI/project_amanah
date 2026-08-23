"""`/v1/items` — the authenticated-safe item collection.

One filter, sort, and pagination path over the item projection. Authentication is
attached to the router, so no operation here can become anonymous by omission.

`/v1/news` used to live here as the same projection with the content kind pinned
to news. It moved to `amanah.api.v1.news` in B-S9: an ingested article is not a
classified item, and serving it through a model that carries a hate label, a
score, and a review state invited precisely the reading `spec.md` section 3.3
forbids. Classified news *item cards* are still served from here.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from amanah.api.dependencies import DatabaseSession, build_response_meta, get_settings
from amanah.api.errors import ApiError, ResourceNotFoundError
from amanah.api.schemas.common import CursorPage, PageInfo
from amanah.api.schemas.errors import ErrorCode
from amanah.api.schemas.filters import ItemListQuery
from amanah.api.schemas.items import ItemDetailResponse, ItemSummary
from amanah.api.v1.mappers import to_item_detail, to_item_summary
from amanah.db.pagination import InvalidCursorError
from amanah.db.repositories.items import ItemRepository
from amanah.settings import Settings

router = APIRouter(tags=["items"])


def _invalid_cursor() -> ApiError:
    """A rejected cursor is a client error, not an empty page.

    Returning page one instead would silently show the caller data they did not
    ask for, which is the same failure mode as broadening an unsupported filter.
    """
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=400,
        message="The pagination cursor is not valid for this request.",
        details={"fields": ["cursor"]},
    )


def _read_page(
    session: DatabaseSession, settings: Settings, query: ItemListQuery
) -> CursorPage[ItemSummary]:
    repository = ItemRepository(session)
    try:
        page = repository.list_items(
            filters=query,
            sort=query.sort,
            limit=query.limit,
            cursor=query.cursor,
            content_kinds=None,
        )
    except InvalidCursorError as exc:
        raise _invalid_cursor() from exc

    return CursorPage[ItemSummary](
        items=[to_item_summary(row) for row in page.rows],
        page=PageInfo(next_cursor=page.next_cursor, limit=query.limit),
        meta=build_response_meta(settings),
    )


@router.get("/items", summary="List authenticated-safe items")
def list_items(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[ItemListQuery, Query()],
) -> CursorPage[ItemSummary]:
    """Return one page of items matching the validated filters."""
    return _read_page(session, settings, query)


@router.get("/items/{item_id}", summary="Read one authenticated-safe item")
def read_item(
    item_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ItemDetailResponse:
    """Return the item detail, including the model disclosure and limitations."""
    row = ItemRepository(session).get_item(item_id)
    if row is None:
        raise ResourceNotFoundError("This item was not found.")
    return ItemDetailResponse(item=to_item_detail(row), meta=build_response_meta(settings))
