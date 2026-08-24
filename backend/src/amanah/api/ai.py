"""Request-scoped construction of the AI boundary.

One place builds a `GeminiClient`, so no route can assemble one with a different
prompt registry, a missing budget, or a wider transport. The registry and the
cache are process-wide — they hold no per-user state and a cold cache on every
request would defeat the point of caching at all — while the token budget is
per-request.

A per-request budget is the honest shape for an API call. `TokenBudget`'s "run"
ceiling bounds one ETL run; on the API side the equivalent unit is one request,
and the daily ceiling that actually guards cost is enforced by the shared tracker
below. Sharing that one tracker across requests is what makes the daily figure
mean anything.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from amanah.api.dependencies import get_settings
from amanah.ml.budgets import TokenBudget
from amanah.ml.cache import InferenceCache
from amanah.ml.catalog import build_registry
from amanah.ml.gemini import GeminiClient
from amanah.ml.prompts import PromptRegistry
from amanah.ml.rate_limits import (
    ASSISTANT_REQUESTS_PER_WINDOW,
    ASSISTANT_WINDOW,
    FixedWindowRateLimiter,
)
from amanah.settings import Settings

#: Built once. The prompts are immutable and reading them is not per-request work.
_REGISTRY: PromptRegistry = build_registry()

#: Shared so a repeated question over unchanged data costs nothing, and so the
#: daily token ceiling is measured across the process rather than per request.
_CACHE = InferenceCache()

_ASSISTANT_LIMITER = FixedWindowRateLimiter(
    limit=ASSISTANT_REQUESTS_PER_WINDOW, window=ASSISTANT_WINDOW
)


def get_prompt_registry() -> PromptRegistry:
    """The registered prompts this deployment may use."""
    return _REGISTRY


def get_assistant_limiter() -> FixedWindowRateLimiter:
    """The per-user assistant allowance."""
    return _ASSISTANT_LIMITER


def get_gemini_client(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GeminiClient:
    """Build the policy-gated client for this request.

    The daily budget tracker lives on application state so every request charges
    the same ceiling. When it is absent — a test app, or the first request after
    a restart — one is created, which is the correct behaviour rather than a
    fallback: a fresh process has spent nothing.
    """
    budget: TokenBudget | None = getattr(request.app.state, "token_budget", None)
    if budget is None:
        budget = TokenBudget(
            per_run_tokens=settings.gemini_per_run_token_budget,
            daily_tokens=settings.gemini_daily_token_budget,
        )
        request.app.state.token_budget = budget

    return GeminiClient(
        settings=settings,
        registry=_REGISTRY,
        budget=budget,
        cache=_CACHE,
    )


GeminiDependency = Annotated[GeminiClient, Depends(get_gemini_client)]
