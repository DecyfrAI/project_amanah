"""`GET /v1/news` — the context news stream (B-S9.8, reconciliation G5).

Articles here coincide with the monitoring window. They are not classifications,
and this route has no way to say otherwise: the projection it reads carries no
label, score, severity, or review state, and the response model has no field to
put one in.

The window is the contract's own: two inclusive UTC calendar dates, defaulting to
the dashboard's default span so headlines line up with the figures beside them.
An empty page is always accompanied by coverage, so "collection failed" and
"nothing on topic was published" stay distinguishable — a gap is never rendered
as a zero.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from amanah.api.dependencies import DatabaseSession, build_response_meta, get_settings
from amanah.api.errors import ApiError
from amanah.api.schemas.errors import ErrorCode
from amanah.api.schemas.news import (
    NewsCoverage,
    NewsListResponse,
    NewsQuery,
    NewsWindow,
    RequestedWindow,
)
from amanah.api.v1.mappers import to_news_item
from amanah.db.pagination import InvalidCursorError
from amanah.db.repositories.news import NewsRepository
from amanah.settings import Settings

router = APIRouter(tags=["news"])

#: The dashboard's default span. The news stream shares it so a reader compares
#: headlines and figures over the same days without having to align them.
DEFAULT_WINDOW_DAYS = 30

#: Widest window this route will answer, so one request cannot ask for the whole
#: archive as a single page scan.
MAXIMUM_WINDOW_DAYS = 400


def _invalid(message: str, field: str) -> ApiError:
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=400,
        message=message,
        details={"fields": [field]},
    )


@router.get("/news", summary="Read the context news stream")
def list_news(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    query: Annotated[NewsQuery, Query()],
) -> NewsListResponse:
    """Return one page of articles published in the requested window."""
    from_date, to_date = query.from_date, query.to_date
    requested_to = to_date or datetime.now(UTC).date()
    requested_from = from_date or requested_to - timedelta(days=DEFAULT_WINDOW_DAYS)
    if requested_to < requested_from:
        raise _invalid("The window end precedes its start.", "from")
    if (requested_to - requested_from).days > MAXIMUM_WINDOW_DAYS:
        raise _invalid(f"A news window may cover at most {MAXIMUM_WINDOW_DAYS} days.", "from")

    try:
        page = NewsRepository(session).read_window(
            window_start=datetime.combine(requested_from, time.min, tzinfo=UTC),
            # Inclusive at both ends: `to` names a day, and a reader asking for
            # today expects today's articles rather than only midnight's.
            window_end=datetime.combine(requested_to, time.max, tzinfo=UTC),
            limit=query.limit,
            cursor=query.cursor,
        )
    except InvalidCursorError as exc:
        raise _invalid("The pagination cursor is not valid for this request.", "cursor") from exc

    return NewsListResponse(
        window=RequestedWindow(from_date=requested_from, to_date=requested_to),
        applied=NewsWindow(from_date=requested_from, to_date=requested_to),
        coverage=NewsCoverage(
            sources=list(page.sources),
            items_retrieved=page.total_in_window,
            last_successful_run=page.last_successful_run,
            warnings=list(page.warnings),
        ),
        data_mode=settings.data_mode,
        next_cursor=page.next_cursor,
        items=[to_news_item(row) for row in page.rows],
        meta=build_response_meta(
            settings, is_stale=bool(page.warnings), warnings=list(page.warnings)
        ),
    )
