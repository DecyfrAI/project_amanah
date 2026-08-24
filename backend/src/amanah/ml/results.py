"""Typed outcomes of one model call (B-S13.8).

Every path out of the Gemini boundary is one of these five values, and none of
them is an exception. That is deliberate: `rules/general.md` §69 keeps exceptions
for unexpected states, and a spent budget, a refused transfer, or a provider
outage are all states this system expects and has a documented behaviour for.
Returning them as values forces each caller to decide what to store, which is how
`ai_deferred` reaches the screen instead of a stack trace.

`InferenceStatus` in `amanah.domain.enums` is the stored form of the same set, so
an outcome here maps onto a prediction row without a second vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from amanah.domain.enums import InferenceStatus


@dataclass(frozen=True, slots=True)
class InferenceUsage:
    """What one call cost, for budgets and for `rules/ml.md` cost telemetry."""

    prompt_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class InferenceSuccess[PayloadT]:
    """Validated structured output, plus how it was produced."""

    payload: PayloadT
    model_name: str
    prompt_id: str
    prompt_version: str
    usage: InferenceUsage = field(default_factory=InferenceUsage)
    was_cached: bool = False

    status: InferenceStatus = InferenceStatus.succeeded


@dataclass(frozen=True, slots=True)
class InferenceDeferred:
    """A budget or quota is spent. Try later; do not treat as a finding.

    Distinct from a failure because the item is still classifiable — nothing about
    it was rejected. `spec.md` section 11.2 requires the rest of the site to stay
    operational while items sit in this state.
    """

    reason: str
    status: InferenceStatus = InferenceStatus.deferred


@dataclass(frozen=True, slots=True)
class InferencePolicyBlocked:
    """Policy forbids sending this material. Never retried under the same policy."""

    reason: str
    status: InferenceStatus = InferenceStatus.policy_blocked


@dataclass(frozen=True, slots=True)
class InferenceInvalidOutput:
    """The provider answered, but not in the shape the schema requires.

    Routed to human review rather than silently discarded: a model that stopped
    honouring its schema is a signal about the model, not a missing row.
    """

    reason: str
    status: InferenceStatus = InferenceStatus.invalid_output


@dataclass(frozen=True, slots=True)
class InferenceProviderFailure:
    """The provider was unreachable, timed out, or refused the request."""

    safe_code: str
    is_retryable: bool
    status: InferenceStatus = InferenceStatus.provider_failure


#: Everything that is not a success. Grouped because callers overwhelmingly want
#: "did this produce labels, or do I record a non-answer?" rather than five
#: separate branches.
type InferenceFailure = (
    InferenceDeferred | InferencePolicyBlocked | InferenceInvalidOutput | InferenceProviderFailure
)

type InferenceResult[PayloadT] = InferenceSuccess[PayloadT] | InferenceFailure


def failure_reason(failure: InferenceFailure) -> str:
    """The stable safe code of any non-success outcome."""
    if isinstance(failure, InferenceProviderFailure):
        return failure.safe_code
    return failure.reason


def describe(result: InferenceResult[Any]) -> dict[str, str | bool | int]:
    """Log-safe description of an outcome.

    Never includes the payload. A classification payload is derived from source
    text and can echo it back through a rationale, and `rules/security.md` keeps
    harmful content out of logs.
    """
    if isinstance(result, InferenceSuccess):
        return {
            "status": result.status.value,
            "was_cached": result.was_cached,
            "total_tokens": result.usage.total_tokens,
        }
    return {"status": result.status.value, "reason": failure_reason(result)}
