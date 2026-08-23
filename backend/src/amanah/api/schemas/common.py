"""Response metadata, rates, coverage, and cursor pagination shared by `/v1`."""

from typing import Self

from pydantic import Field, computed_field, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.domain.enums import DataMode

#: Cursors are opaque to clients. The bound exists so an oversized value is
#: rejected at the boundary instead of reaching the repository layer.
MAX_CURSOR_LENGTH = 512

DEFAULT_PAGE_LIMIT = 25
MAX_PAGE_LIMIT = 100


class ResponseMeta(ResponseModel):
    """Envelope metadata attached to every product response."""

    request_id: str = Field(min_length=1)
    generated_at: UtcDatetime
    data_mode: DataMode
    is_stale: bool = False
    warnings: list[str] = Field(
        default_factory=list,
        description="Safe coverage or freshness warnings, never provider error text.",
    )


class MetricRate(ResponseModel):
    """A rate that always discloses how it was computed.

    A rate is never reported as a bare percentage: the numerator, denominator,
    date window, source scope, coverage, and data mode travel with it. When the
    denominator is zero the value is `null` — a gap, never zero.
    """

    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    window_start: UtcDatetime
    window_end: UtcDatetime
    source_scope: list[str] = Field(
        description="Sources or sampling strata the denominator was drawn from."
    )
    coverage_score: float | None = Field(default=None, ge=0.0, le=1.0)
    data_mode: DataMode

    @computed_field  # type: ignore[prop-decorator]
    @property
    def value(self) -> float | None:
        """Numerator over denominator, or `None` when nothing was observed."""
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator

    @model_validator(mode="after")
    def _check_bounds(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("numerator must not exceed denominator")
        if self.window_start > self.window_end:
            raise ValueError("window_start must not be after window_end")
        return self


class CoverageSummary(ResponseModel):
    """Freshness and collection coverage shown before or beside aggregate metrics."""

    last_success_at: UtcDatetime | None
    coverage_score: float | None = Field(default=None, ge=0.0, le=1.0)
    data_mode: DataMode
    is_stale: bool
    warnings: list[str] = Field(default_factory=list)


class PageInfo(ResponseModel):
    """Cursor pagination state.

    `next_cursor` is `null` on the last page. `rules/api.md` section 7.4 prefers
    absolute `next`/`prev` link URLs; this contract returns an opaque cursor
    instead because the frontend rebuilds requests from validated filter state
    and shares one response model between fixture and live providers.
    """

    next_cursor: str | None = Field(default=None, max_length=MAX_CURSOR_LENGTH)
    limit: int = Field(ge=1, le=MAX_PAGE_LIMIT)


class CursorPageRequest(RequestModel):
    """Query parameters accepted by every cursor-paginated collection."""

    cursor: str | None = Field(default=None, max_length=MAX_CURSOR_LENGTH)
    limit: int = Field(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT)


class CursorPage[ItemT](ResponseModel):
    """Paginated collection response."""

    items: list[ItemT]
    page: PageInfo
    meta: ResponseMeta
