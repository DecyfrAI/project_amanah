"""Contract for snapshot insights, discussion, captures, and reactions (B-S27).

The shape encodes ADR 0004. An insight carries its numerator *and* its
denominator, so a claim can be checked rather than believed. A post belongs to an
insight — there is no model here for a thread without one. Reactions are two
counts and the caller's own choice; there is no field anywhere that totals a
person, and adding one would be a contract change a reviewer would see.
"""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import Field, computed_field, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import CursorPageRequest, ResponseMeta
from amanah.db.models.discussion import MAXIMUM_CLAIM_LENGTH, MAXIMUM_POST_LENGTH
from amanah.domain.enums import OnboardingStatus, ReactionKind

#: Captures and Explorer links are first-party paths. An absolute URL would point
#: the reader at somebody else's server, which ADR 0004 refused. The second
#: slash is excluded deliberately: `//evil.example` is protocol-relative, and a
#: browser resolves it against the current scheme and leaves the site.
#: Written without look-ahead: pydantic compiles patterns with a Rust engine
#: that does not support it.
FIRST_PARTY_PATH_PATTERN = r"^/([^/\s][^\s]*)?$"

#: A filter hash identifies the filter state a figure was read under. It is a
#: hex digest, so anything else is a client sending the wrong thing.
FILTER_HASH_PATTERN = r"^[0-9a-f]{8,64}$"


class UpdateProfileRequest(RequestModel):
    """`PATCH /v1/me` body (B-S27.1).

    Role is deliberately absent. It comes from the verified token, and accepting
    one here would let a client name its own privileges; `extra="forbid"` turns
    an attempt into a validation error rather than a silently ignored field.
    """

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    onboarding_status: OnboardingStatus | None = None
    content_safety_preferences: dict[str, bool] | None = Field(
        default=None,
        description="Reveal preferences for redacted text and blurred media.",
    )

    @model_validator(mode="after")
    def _check_not_empty(self) -> Self:
        if (
            self.display_name is None
            and self.onboarding_status is None
            and self.content_safety_preferences is None
        ):
            raise ValueError("a profile update must change at least one field")
        return self


class CreateInsightRequest(RequestModel):
    """`POST /v1/insights` body.

    The counts arrive with the claim because ADR 0004 makes the snapshot
    checkable: a reader compares the claim against the same numerator and
    denominator the author was looking at, not against a live query that has
    moved on since.
    """

    title: str = Field(min_length=1, max_length=200)
    claim: str = Field(min_length=1, max_length=MAXIMUM_CLAIM_LENGTH)
    metric: str = Field(min_length=1, max_length=100)
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    window_start: UtcDatetime
    window_end: UtcDatetime
    figure_label: str = Field(min_length=1, max_length=200)
    filter_hash: str = Field(pattern=FILTER_HASH_PATTERN)
    explorer_href: str = Field(max_length=2000, pattern=FIRST_PARTY_PATH_PATTERN)
    source_keys: list[str] = Field(default_factory=list, max_length=50)
    items_observed: int = Field(ge=0)
    items_relevant: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_counts(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("numerator must not exceed denominator")
        if self.items_relevant > self.items_observed:
            raise ValueError("items_relevant must not exceed items_observed")
        if self.window_start > self.window_end:
            raise ValueError("window_start must not be after window_end")
        return self


class InsightSummary(ResponseModel):
    """One frozen figure and the counts behind it."""

    id: UUID
    author_id: UUID
    author_display_name: str | None
    title: str
    claim: str
    metric: str
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    window_start: UtcDatetime
    window_end: UtcDatetime
    figure_label: str
    filter_hash: str
    explorer_href: str
    source_keys: list[str]
    items_observed: int = Field(ge=0)
    items_relevant: int = Field(ge=0)
    created_at: UtcDatetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def value(self) -> float | None:
        """The rate the claim states, or `None` when nothing was observed.

        A zero denominator is a gap, never a zero rate. Deriving it here rather
        than storing it keeps one arithmetic authority, the same as `MetricRate`.
        """
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator


class InsightResponse(ResponseModel):
    """`POST /v1/insights` and `GET /v1/insights/{id}` payload."""

    insight: InsightSummary
    meta: ResponseMeta


class CreateCaptureRequest(RequestModel):
    """`POST /v1/captures` body.

    `image_source` is a first-party path to a figure this product rendered.
    Uploaded pixels never enter here: ADR 0004 refused a screenshot board because
    it would redistribute the material the product exists to measure.
    """

    alt_text: str = Field(min_length=1, max_length=300)
    image_source: str = Field(max_length=2000, pattern=FIRST_PARTY_PATH_PATTERN)
    filter_hash: str = Field(pattern=FILTER_HASH_PATTERN)
    explorer_href: str = Field(max_length=2000, pattern=FIRST_PARTY_PATH_PATTERN)


class CaptureSummary(ResponseModel):
    """One stored first-party figure capture."""

    id: UUID
    alt_text: str
    image_source: str
    filter_hash: str
    explorer_href: str
    created_at: UtcDatetime


class CaptureResponse(ResponseModel):
    """`POST /v1/captures` payload."""

    capture: CaptureSummary
    meta: ResponseMeta


class PostReactionCounts(ResponseModel):
    """Counts on one note, plus whichever reaction the caller left.

    Two counts and one nullable choice. Nothing here identifies who reacted, and
    nothing anywhere sums these across an author's posts.
    """

    useful: int = Field(default=0, ge=0)
    needs_context: int = Field(default=0, ge=0)
    viewer: ReactionKind | None = None


class DiscussionPostEntry(ResponseModel):
    """One note in a thread, retracted or not."""

    id: UUID
    snapshot_insight_id: UUID
    author_id: UUID
    author_display_name: str | None
    body: str = Field(description="Replaced with a fixed notice once the author retracts it.")
    created_at: UtcDatetime
    retracted_at: UtcDatetime | None = None
    capture: CaptureSummary | None = None
    reactions: PostReactionCounts


class ViewerPostEntry(DiscussionPostEntry):
    """One of the caller's own notes, with enough of its parent to find it."""

    insight_title: str


class DiscussionResponse(ResponseModel):
    """`GET /v1/insights/{id}/discussion` payload."""

    insight_id: UUID
    posts: list[DiscussionPostEntry]
    can_participate: bool = Field(
        description="Whether the caller holds an invitation to post (ADR 0004)."
    )
    meta: ResponseMeta


class CreatePostRequest(RequestModel):
    """`POST /v1/insights/{id}/discussion/posts` body."""

    body: str = Field(min_length=1, max_length=MAXIMUM_POST_LENGTH)
    capture_id: UUID | None = Field(
        default=None, description="One of the caller's own first-party captures."
    )


class PostResponse(ResponseModel):
    """One note, returned after it is added or retracted."""

    post: DiscussionPostEntry
    meta: ResponseMeta


class ReactRequest(RequestModel):
    """`POST /v1/posts/{id}/reactions` body."""

    kind: ReactionKind


class InsightListQuery(CursorPageRequest):
    """Validated paging for the insight list. No filters yet, and none implied."""


class ViewerPostQuery(CursorPageRequest):
    """Validated paging for `GET /v1/me/posts`."""
