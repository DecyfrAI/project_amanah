"""The context news stream contract for `GET /v1/news` (B-S9.8, reconciliation G5).

This is deliberately **not** an item projection. Milestone 2 shipped `/v1/news`
as `CursorPage[ItemSummary]`, which gave every article a hate label, a score, and
a review state. An ingested article is published journalism that *coincides* with
a monitoring window; it is not an Amanah finding, and giving it the shape of one
invites exactly the reading `spec.md` section 3.3 forbids.

So no field here carries a classification, a confidence, a severity, or a review
state, and there is nowhere to put one. Classified news items remain a separate
surface served by `/v1/items`.

The field names are the ones agreed in `docs/news-rss-sources.md`, which the
frontend already validates against. They stay `snake_case` and are not reshaped
to match the camelCase used inside other dashboard contracts.
"""

from __future__ import annotations

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_CURSOR_LENGTH,
    MAX_PAGE_LIMIT,
    ResponseMeta,
)
from amanah.domain.enums import DataMode, NewsScope


class NewsWindow(ResponseModel):
    """A UTC calendar window, inclusive at both ends.

    `from` and `to` are the names the agreed contract uses, and `from` is a
    Python keyword, so the fields carry a serialization alias rather than being
    renamed. FastAPI serializes responses by alias, so the JSON matches the
    contract while the Python attribute stays usable.
    """

    from_date: date = Field(serialization_alias="from")
    to_date: date = Field(serialization_alias="to")

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.to_date < self.from_date:
            raise ValueError("to must not precede from")
        return self


class RequestedWindow(NewsWindow):
    """The window as asked for, with its timezone stated rather than assumed."""

    timezone: str = "UTC"


class NewsCoverage(ResponseModel):
    """What this window actually covers, so an empty list can be read correctly.

    An empty `items` with a warning is a gap. An empty `items` with no warning
    and a recent `last_successful_run` means collection worked and found nothing
    on topic. The two look identical without this block, which is why it is
    required rather than optional.
    """

    sources: list[str] = Field(
        default_factory=list, description="Publishers that contributed to this window."
    )
    items_retrieved: int = Field(ge=0)
    last_successful_run: UtcDatetime | None = None
    warnings: list[str] = Field(
        default_factory=list,
        description="Publishable coverage gaps. Never a provider error body.",
    )


class NewsItem(ResponseModel):
    """One published article. No label, no score, no review state — by design."""

    id: UUID
    source_name: str
    source_homepage: str
    title: str
    summary: str
    url: str
    published_at: UtcDatetime | None = Field(
        default=None,
        description="Null when the feed did not state one; never the retrieval time.",
    )
    retrieved_at: UtcDatetime
    language: str
    scope: NewsScope | None = Field(
        default=None,
        description=(
            "Null when the source did not state a scope. `geographic_scope` is a "
            "free-text column shared with other content kinds, so a value that is "
            "not one of the two is reported as absent rather than coerced into "
            "the nearer-looking one."
        ),
    )
    location: str | None = None


class NewsListResponse(ResponseModel):
    """One page of the context news stream."""

    window: RequestedWindow
    applied: NewsWindow
    coverage: NewsCoverage
    data_mode: DataMode
    next_cursor: str | None = None
    items: list[NewsItem] = Field(default_factory=list)
    meta: ResponseMeta


class NewsQuery(RequestModel):
    """Query parameters accepted by the news stream.

    Deliberately short. Platform, hate-type, severity, and review filters do not
    exist here because none of them means anything for an unclassified article,
    and `RequestModel` forbids unknown fields — so asking for one is a client
    error rather than a query the server quietly widens.

    `from` and `to` are aliases because `from` is a Python keyword.
    """

    from_date: date | None = Field(default=None, alias="from")
    to_date: date | None = Field(default=None, alias="to")
    cursor: str | None = Field(default=None, max_length=MAX_CURSOR_LENGTH)
    limit: int = Field(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT)
