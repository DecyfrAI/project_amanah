"""Safe connector and coverage state.

Nothing here can carry a secret: there is no field for a key, a connection
string, a host, or a provider response body, and the status is a closed
vocabulary rather than free text. A connector that is failing reports
`degraded` with a publishable warning; why it is failing stays in the logs.
"""

from pydantic import Field

from amanah.api.schemas.base import ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import ConnectorStatus, DataMode, PublicPlatform, SourceKind


class ConnectionState(ResponseModel):
    """One configured source and how it is currently doing."""

    source_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: SourceKind
    platform: PublicPlatform
    purpose: str = Field(min_length=1, description="Why this source is collected.")
    policy_url: str | None = None
    status: ConnectorStatus
    is_enabled: bool
    last_success_at: UtcDatetime | None
    last_checked_at: UtcDatetime | None
    warning: str | None = Field(
        default=None,
        description="Publishable coverage warning. Never a provider error body.",
    )


class ConnectionsResponse(ResponseModel):
    """`GET /v1/connections` payload."""

    connections: list[ConnectionState] = Field(default_factory=list)
    data_mode: DataMode
    last_success_at: UtcDatetime | None
    meta: ResponseMeta
