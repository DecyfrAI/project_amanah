"""Authenticated-safe projections of collected content.

These models are deliberately incomplete views of `content_item`. Raw or
encrypted text, private storage keys, author identifiers, and internal evidence
have no field here, so they cannot leak by adding a value to an existing route.
"""

from uuid import UUID

from pydantic import Field, computed_field

from amanah.api.schemas.base import ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.api.schemas.filters import CountryCode, DatasetIdentifier, NarrativeTag
from amanah.domain.enums import (
    NOT_APPLICABLE_DISPLAY,
    ConfidenceTier,
    ContentKind,
    HateType,
    PublicPlatform,
    Relevance,
    ReviewState,
    Severity,
    SourceStatus,
    Stance,
)


class DatasetProvenance(ResponseModel):
    """Dataset lineage for a row imported from a reviewed open datapack.

    The public platform of such an item is `not_applicable`; this block is how a
    reader still learns where the row came from.
    """

    provider: DatasetIdentifier
    name: DatasetIdentifier
    version: DatasetIdentifier
    license_id: str | None
    landing_page_url: str | None


class ItemSummary(ResponseModel):
    """Item projection used in lists and cards."""

    id: UUID
    content_kind: ContentKind
    platform: PublicPlatform
    title: str | None
    permitted_excerpt: str | None = Field(
        default=None,
        description="Licensed or fair-use excerpt only; never full source text.",
    )
    publisher_or_container: str | None
    canonical_url: str | None
    published_at: UtcDatetime | None
    observed_at: UtcDatetime
    language: str | None
    country_code: CountryCode | None
    source_status: SourceStatus
    is_fixture: bool
    dataset: DatasetProvenance | None = None

    relevance: Relevance
    stance: Stance
    hate_types: list[HateType] = Field(default_factory=list)
    severity: Severity
    confidence_tier: ConfidenceTier
    review_state: ReviewState
    requires_review: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def platform_display(self) -> str:
        """Human-facing platform label; open-datapack rows display as `N/A`."""
        if self.platform is PublicPlatform.not_applicable:
            return NOT_APPLICABLE_DISPLAY
        return self.platform.value


class ItemDetail(ItemSummary):
    """Item projection used on the item page.

    Adds the model disclosure required alongside any classification: the exact
    score, the model and prompt versions that produced it, when it ran, the
    rationale, and the stated limitations.
    """

    score: float = Field(ge=0.0, le=1.0)
    model_name: str
    model_version: str
    prompt_version: str
    taxonomy_version: str
    inferred_at: UtcDatetime | None
    rationale: str | None
    narrative_tags: list[NarrativeTag] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    sampling_disclosure: str = Field(
        description="What this monitored sample does and does not represent."
    )


class ItemDetailResponse(ResponseModel):
    """Single-item response envelope."""

    item: ItemDetail
    meta: ResponseMeta
