"""`POST /v1/assistant/query` request and response contracts (spec §13.2, v2.2).

Matches the frontend `AssistantAskInput` and `AssistantReply` in
`apps/web/src/api/contracts.ts`. The request carries the question *and* the exact
dashboard filters, so a reply can never describe a different sample from the one
the reader is looking at — which is the reason the filters are in the body rather
than inferred from a session.
"""

from __future__ import annotations

from pydantic import Field

from amanah.api.schemas.base import RequestModel, ResponseModel
from amanah.api.schemas.common import ResponseMeta
from amanah.api.schemas.filters import ItemFilters
from amanah.ml.assistant import MAX_QUESTION_LENGTH
from amanah.ml.assistant_schema import CitationKind, GroundedIn


class AssistantQueryRequest(RequestModel):
    """A question about the currently filtered window.

    `filters` reuses the same validated model the dashboard uses, so an
    unsupported filter is rejected here exactly as it would be on `/v1/dashboard`
    rather than quietly widening the sample the answer describes.
    """

    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    filters: ItemFilters = Field(default_factory=ItemFilters)


class AssistantCitationOut(ResponseModel):
    """A pointer to the stored figure or methodology note behind a claim."""

    kind: CitationKind
    id: str
    label: str


class AssistantQueryResponse(ResponseModel):
    """The verified reply.

    `grounded_in` is `none` for an abstention, and an abstention is a normal
    outcome rather than an error: the endpoint returns `200` with an honest "the
    dashboard does not hold that" instead of a plausible sentence.
    """

    answer: str
    citations: list[AssistantCitationOut] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    grounded_in: GroundedIn
    meta: ResponseMeta
