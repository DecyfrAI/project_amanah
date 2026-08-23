"""Validated filters and sorts for authenticated item, news, and dashboard reads.

An unsupported filter or sort is a client error. Nothing here silently widens a
query: unknown fields are rejected, list filters are bounded, and the date window
has a maximum span.
"""

from datetime import timedelta
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from amanah.api.schemas.base import RequestModel, UtcDatetime
from amanah.domain.enums import (
    ConfidenceTier,
    ContentKind,
    PublicPlatform,
    ReviewState,
    Severity,
)

#: Longest date range a single query may span. Longer windows must be requested
#: as separate pages of research reports rather than one unbounded scan.
MAX_FILTER_WINDOW = timedelta(days=366)

#: Upper bound on any multi-value filter, so a request cannot smuggle in a very
#: large `IN (...)` list.
MAX_FILTER_VALUES = 25

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
NarrativeTag = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=64)
]
DatasetIdentifier = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class ItemSort(StrEnum):
    """Documented sort orders. Every value maps to an indexed column plus a
    stable secondary key so pages do not drift."""

    newest = "newest"
    oldest = "oldest"
    highest_confidence = "highest_confidence"
    lowest_confidence = "lowest_confidence"
    highest_severity = "highest_severity"


class ItemFilters(RequestModel):
    """Filters accepted by authenticated item, news, and dashboard reads.

    Dataset provenance filters are separate from `platforms`: open-datapack rows
    publish `not_applicable` as their platform while keeping dataset provider,
    name, and version filterable.
    """

    date_from: UtcDatetime | None = None
    date_to: UtcDatetime | None = None
    content_kinds: list[ContentKind] | None = Field(default=None, max_length=MAX_FILTER_VALUES)
    platforms: list[PublicPlatform] | None = Field(default=None, max_length=MAX_FILTER_VALUES)
    dataset_provider: DatasetIdentifier | None = None
    dataset_name: DatasetIdentifier | None = None
    dataset_version: DatasetIdentifier | None = None
    country_codes: list[CountryCode] | None = Field(default=None, max_length=MAX_FILTER_VALUES)
    narrative_tags: list[NarrativeTag] | None = Field(default=None, max_length=MAX_FILTER_VALUES)
    severities: list[Severity] | None = Field(default=None, max_length=MAX_FILTER_VALUES)
    review_states: list[ReviewState] | None = Field(default=None, max_length=MAX_FILTER_VALUES)
    confidence_tiers: list[ConfidenceTier] | None = Field(
        default=None, max_length=MAX_FILTER_VALUES
    )

    @model_validator(mode="after")
    def _check_window(self) -> Self:
        if self.date_from is None or self.date_to is None:
            return self
        if self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        if self.date_to - self.date_from > MAX_FILTER_WINDOW:
            raise ValueError(f"date range must not exceed {MAX_FILTER_WINDOW.days} days")
        return self
