"""`POST /v1/assistant/query` — grounded questions about the filtered window."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from amanah.api.ai import GeminiDependency, get_assistant_limiter
from amanah.api.dependencies import CurrentUser, DatabaseSession, build_response_meta, get_settings
from amanah.api.errors import RateLimitedError
from amanah.api.schemas.assistant import (
    AssistantCitationOut,
    AssistantQueryRequest,
    AssistantQueryResponse,
)
from amanah.metrics.facts import build_fact_bundle
from amanah.ml.assistant import AssistantService
from amanah.ml.rate_limits import FixedWindowRateLimiter
from amanah.settings import Settings

router = APIRouter(tags=["assistant"])


@router.post("/assistant/query", summary="Ask a grounded question about the current window")
def ask_assistant(
    body: AssistantQueryRequest,
    user: CurrentUser,
    session: DatabaseSession,
    client: GeminiDependency,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[FixedWindowRateLimiter, Depends(get_assistant_limiter)],
) -> AssistantQueryResponse:
    """Answer from stored facts, or say plainly that the data cannot answer.

    The filters in the body are the ones the reader has applied, so the fact
    bundle is built from exactly the sample on their screen. An answer therefore
    cannot describe a different window from the figures beside it.
    """
    decision = limiter.check(user.user_id)
    if not decision.is_allowed:
        raise RateLimitedError(
            retry_after_seconds=decision.retry_after_seconds,
            message="Too many assistant questions. Try again shortly.",
        )

    bundle = build_fact_bundle(session, filters=body.filters, data_mode=settings.data_mode)
    answer = AssistantService(client=client).answer(question=body.question, bundle=bundle)

    return AssistantQueryResponse(
        answer=answer.output.answer,
        citations=[
            AssistantCitationOut(kind=citation.kind, id=citation.id, label=citation.label)
            for citation in answer.output.citations
        ],
        limitations=list(answer.output.limitations),
        grounded_in=answer.output.grounded_in,
        meta=build_response_meta(settings, warnings=list(bundle.coverage_warnings)),
    )
