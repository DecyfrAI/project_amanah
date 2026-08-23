"""Curated education-resource contract for authenticated base-role readers.

Only reviewed, published entries are ever projected through this model, so it
carries no draft or governance state.
"""

from uuid import UUID

from pydantic import Field

from amanah.api.schemas.base import ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import ResourceCategory


class ResourceEntry(ResponseModel):
    """A reviewed external resource."""

    id: UUID
    title: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    url: str = Field(description="Absolute HTTPS URL of the official resource.")
    country_scope: str = Field(
        description="ISO country code, a multi-country grouping, or 'global'."
    )
    category: ResourceCategory
    summary: str = Field(min_length=1)
    last_reviewed_at: UtcDatetime


class ResourceListResponse(ResponseModel):
    """`GET /v1/resources` payload.

    The catalogue is small and curated, so it is returned whole rather than
    paginated; `rules/api.md` requires cursor pagination for collections that
    change, and this one changes only through reviewer action.
    """

    resources: list[ResourceEntry] = Field(default_factory=list)
    categories: list[ResourceCategory] = Field(default_factory=list)
    meta: ResponseMeta
