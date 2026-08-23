"""`/v1/items` and `/v1/news` — the authenticated-safe item collections.

Both routes read the same projection and share one filter, sort, and pagination
path; `/v1/news` differs only in restricting the content kind. Authentication is
attached to the router, so neither operation can become anonymous by omission.
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
from amanah.domain.enums import ContentKind
from amanah.settings import Settings

router = APIRouter(tags=["items"])

#: `/v1/news` is the current-events view of the same store.
NEWS_CONTENT_KINDS = (ContentKind.news_article,)


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
    session: DatabaseSession,
    settings: Settings,
    query: ItemListQuery,
    content_kinds: tuple[ContentKind, ...] | None,
) -> CursorPage[ItemSummary]:
    repository = ItemRepository(session)
    try:
        page = repository.list_items(
            filters=query,
            sort=query.sort,
            limit=query.limit,
            cursor=query.cursor,
            content_kinds=content_kinds,
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
    return _read_page(session, settings, query, content_kinds=None)


@router.get("/news", summary="List authenticated-safe news items")
def list_news(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[ItemListQuery, Query()],
) -> CursorPage[ItemSummary]:
    """Return one page of news articles matching the validated filters."""
    return _read_page(session, settings, query, content_kinds=NEWS_CONTENT_KINDS)


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
