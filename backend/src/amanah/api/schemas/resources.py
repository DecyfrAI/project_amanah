"""Curated education-resource contracts for readers and catalog governors.

Only reviewed, published entries are ever projected through this model, so it
carries no draft or governance state.
"""

import ipaddress
from typing import Literal, Self
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import PublicationStatus, ResourceCategory

RESOURCE_TITLE_MAX_LENGTH = 200
RESOURCE_ORGANIZATION_MAX_LENGTH = 200
RESOURCE_SUMMARY_MIN_LENGTH = 20
RESOURCE_SUMMARY_MAX_LENGTH = 2_000
RESOURCE_URL_MAX_LENGTH = 2_048
RESOURCE_COUNTRY_SCOPES = frozenset({"global", "CA", "US", "GB"})


def validate_resource_url(value: str) -> str:
    """Accept an absolute public HTTPS link with no embedded credentials."""
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("url must be an absolute HTTPS URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("url must not contain credentials")
    if parts.port not in (None, 443):
        raise ValueError("url must use the standard HTTPS port")
    hostname = parts.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError("url must name a public host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("url must not name a private or reserved address")
    return value


class ResourceFields(RequestModel):
    """Fields a reviewer can curate before publication."""

    title: str = Field(min_length=3, max_length=RESOURCE_TITLE_MAX_LENGTH)
    organization: str = Field(min_length=2, max_length=RESOURCE_ORGANIZATION_MAX_LENGTH)
    url: str = Field(min_length=1, max_length=RESOURCE_URL_MAX_LENGTH)
    country_scope: str
    category: ResourceCategory
    summary: str = Field(
        min_length=RESOURCE_SUMMARY_MIN_LENGTH, max_length=RESOURCE_SUMMARY_MAX_LENGTH
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return validate_resource_url(value)

    @field_validator("country_scope")
    @classmethod
    def _validate_country_scope(cls, value: str) -> str:
        if value not in RESOURCE_COUNTRY_SCOPES:
            allowed = ", ".join(sorted(RESOURCE_COUNTRY_SCOPES))
            raise ValueError(f"country_scope must be one of: {allowed}")
        return value


class CreateResourceRequest(ResourceFields):
    """Create a draft; candidates never publish in the creation request."""


class UpdateResourceRequest(RequestModel):
    """Update curated fields without changing lifecycle state directly."""

    title: str | None = Field(default=None, min_length=3, max_length=RESOURCE_TITLE_MAX_LENGTH)
    organization: str | None = Field(
        default=None, min_length=2, max_length=RESOURCE_ORGANIZATION_MAX_LENGTH
    )
    url: str | None = Field(default=None, min_length=1, max_length=RESOURCE_URL_MAX_LENGTH)
    country_scope: str | None = None
    category: ResourceCategory | None = None
    summary: str | None = Field(
        default=None,
        min_length=RESOURCE_SUMMARY_MIN_LENGTH,
        max_length=RESOURCE_SUMMARY_MAX_LENGTH,
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        return validate_resource_url(value) if value is not None else None

    @field_validator("country_scope")
    @classmethod
    def _validate_country_scope(cls, value: str | None) -> str | None:
        if value is not None and value not in RESOURCE_COUNTRY_SCOPES:
            allowed = ", ".join(sorted(RESOURCE_COUNTRY_SCOPES))
            raise ValueError(f"country_scope must be one of: {allowed}")
        return value

    @model_validator(mode="after")
    def _require_a_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one resource field must be supplied")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("resource fields cannot be null")
        return self


class PublishResourceRequest(RequestModel):
    """The explicit human-review confirmation required for publication."""

    reviewed_summary: Literal[True]


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


class ManagedResourceEntry(ResponseModel):
    """Reviewer/admin projection including lifecycle and governance fields."""

    id: UUID
    title: str
    organization: str
    url: str
    country_scope: str
    category: ResourceCategory
    summary: str
    status: PublicationStatus
    last_reviewed_at: UtcDatetime | None
    reviewed_by: str | None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ManagedResourceResponse(ResponseModel):
    resource: ManagedResourceEntry
    meta: ResponseMeta


class ManagedResourceListResponse(ResponseModel):
    resources: list[ManagedResourceEntry] = Field(default_factory=list)
    meta: ResponseMeta


class ResourceAuditEvent(ResponseModel):
    id: UUID
    resource_entry_id: UUID
    actor_user_id: UUID
    action: Literal["created", "updated", "published", "archived"]
    snapshot: dict[str, object]
    created_at: UtcDatetime


class ResourceAuditResponse(ResponseModel):
    events: list[ResourceAuditEvent] = Field(default_factory=list)
    meta: ResponseMeta


class ResourceListResponse(ResponseModel):
    """`GET /v1/resources` payload.

    The catalogue is small and curated, so it is returned whole rather than
    paginated; `rules/api.md` requires cursor pagination for collections that
    change, and this one changes only through reviewer action.
    """

    resources: list[ResourceEntry] = Field(default_factory=list)
    categories: list[ResourceCategory] = Field(default_factory=list)
    meta: ResponseMeta
