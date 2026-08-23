"""Curated education-resource contract for authenticated base-role readers.

Only reviewed, published entries are ever projected through this model, so it
carries no draft or governance state.
"""

from uuid import UUID

from pydantic import Field

from amanah.api.schemas.base import ResponseModel, UtcDatetime
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
