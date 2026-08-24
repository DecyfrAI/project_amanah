"""The grounded dashboard assistant (B-S25.2 to B-S25.6).

Answers one question about one filtered window, from stored facts only. The
model receives the question and the fact bundle in the same untrusted content
block — the question is data, exactly like a collected post is — and its answer is
verified against the bundle before it is returned.

Three refusals are built in rather than requested.

*No number the bundle does not hold.* Every figure in the answer is matched
against the cited facts by the same validator the insight path uses, so the
assistant and the cached insights cannot disagree about what counts as grounded.

*No causal claim.* Rejected by the schema, deterministically, before the answer
reaches this module.

*No answer at all, when the facts cannot support one.* `grounded_in: none` is a
success, not an error. An assistant that always produces a paragraph is an
assistant that invents one, and this product's whole claim is that its numbers
are checkable.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from amanah.domain.enums import PublicPlatform, RetentionPolicy
from amanah.ml.assistant_schema import AssistantOutput, CitationKind, GroundedIn
from amanah.ml.catalog import ASSISTANT_ANSWER_PROMPT_ID
from amanah.ml.fact_bundle import FactBundle
from amanah.ml.gemini import GeminiClient, InferenceRequest
from amanah.ml.insight_schema import InsightCitation, InsightOutput
from amanah.ml.insights import validate_against_bundle
from amanah.ml.policy import DataClass, TransferRequest
from amanah.ml.results import InferenceSuccess, failure_reason

logger = logging.getLogger(__name__)

#: Longest question accepted. A question is a question; anything longer is either
#: a paste of something else or an attempt to crowd the instructions out of the
#: context window.
MAX_QUESTION_LENGTH = 500

#: Returned whenever the assistant cannot answer. One sentence, no speculation,
#: and no hint about what a differently-worded question might extract.
UNAVAILABLE_ANSWER = (
    "The dashboard does not hold the information needed to answer that for the current "
    "filters. The figures on this page are the complete set of numbers available."
)

#: Attached to every answer. The assistant describes a purposive sample, and a
#: reader who takes one sentence away should take this one.
STANDING_LIMITATIONS = (
    "This answer describes the monitored sample under the current filters only, not any "
    "platform or population.",
    "Labels are produced by an automated model and may be wrong.",
)


@dataclass(frozen=True, slots=True)
class AssistantAnswer:
    """A verified reply, or a typed abstention."""

    output: AssistantOutput
    was_cached: bool = False
    #: Set when the reply is an abstention, naming why in a stable code. `None`
    #: on a grounded answer.
    reason: str | None = None


def abstain(reason: str) -> AssistantAnswer:
    """The typed non-answer, used for every path that cannot ground a reply."""
    return AssistantAnswer(
        output=AssistantOutput(
            answer=UNAVAILABLE_ANSWER,
            citations=[],
            limitations=list(STANDING_LIMITATIONS),
            grounded_in=GroundedIn.none,
        ),
        reason=reason,
    )


class AssistantService:
    """Answers questions about a filtered window from stored facts only."""

    def __init__(self, *, client: GeminiClient) -> None:
        self._client = client

    def answer(self, *, question: str, bundle: FactBundle) -> AssistantAnswer:
        """Answer one question, or abstain with a typed reason."""
        trimmed = question.strip()
        if not trimmed:
            return abstain("empty_question")
        if bundle.is_empty:
            return abstain("insufficient_data")

        result = self._client.infer(
            InferenceRequest(
                prompt_id=ASSISTANT_ANSWER_PROMPT_ID,
                content=_render(trimmed, bundle),
                # Keyed by the question as well as the facts: two different
                # questions over one window are different inferences and must not
                # share a cache entry.
                content_hash=_cache_hash(trimmed, bundle),
                transfer=TransferRequest(
                    data_class=DataClass.derived_aggregate,
                    platform=PublicPlatform.not_applicable,
                    retention_policy=RetentionPolicy.indefinite_permitted,
                ),
            ),
            AssistantOutput,
        )
        if not isinstance(result, InferenceSuccess):
            reason = failure_reason(result)
            logger.info("assistant answer unavailable", extra={"reason": reason})
            return abstain(reason)

        output = result.payload
        if output.grounded_in is GroundedIn.none:
            # The model declined. Its own wording is not returned: an abstention
            # is the one place a model could otherwise editorialise unchecked.
            return abstain("model_abstained")

        problem = _verify(output, bundle)
        if problem is not None:
            logger.warning("assistant answer failed verification", extra={"reason": problem})
            return abstain(problem)

        return AssistantAnswer(
            output=output.model_copy(
                update={"limitations": _with_standing_limitations(output.limitations)}
            ),
            was_cached=result.was_cached,
        )


def _verify(output: AssistantOutput, bundle: FactBundle) -> str | None:
    """Check every citation and every figure against the bundle.

    Reuses the insight validator so one definition of "grounded" governs both
    surfaces. Metric and coverage citations must name a real fact; a methodology
    citation is checked against the bundle's methodology notes instead, since
    those are prose rather than figures.
    """
    for citation in output.citations:
        if citation.kind is CitationKind.methodology:
            if citation.id not in _methodology_ids(bundle):
                return "methodology_citation_not_in_bundle"
            continue
        if bundle.fact(citation.id) is None:
            return "citation_not_in_bundle"

    if output.grounded_in is GroundedIn.methodology:
        # A methodology answer makes no quantitative claim, so there is no figure
        # to verify. The schema already rejected causal wording.
        return None

    # Reuse the numeric validator by expressing the reply in its terms: the same
    # answer text, and the same set of cited facts.
    equivalent = InsightOutput(
        answer=output.answer,
        citations=[
            InsightCitation(fact_id=citation.id, statement=citation.label)
            for citation in output.citations
            if citation.kind is not CitationKind.methodology
        ],
    )
    return validate_against_bundle(equivalent, bundle)


def _methodology_ids(bundle: FactBundle) -> frozenset[str]:
    """Citable ids for the bundle's methodology notes.

    Positional (`methodology.0`) because the notes are a fixed, versioned tuple:
    a stable index is a stable identifier, and inventing slugs for four sentences
    would be a vocabulary nobody else uses.
    """
    return frozenset(f"methodology.{index}" for index in range(len(bundle.methodology_notes)))


def _with_standing_limitations(limitations: list[str]) -> list[str]:
    """Append the disclosures every answer carries, without repeating one."""
    combined = list(limitations)
    for limitation in STANDING_LIMITATIONS:
        if limitation not in combined:
            combined.append(limitation)
    return combined


def _render(question: str, bundle: FactBundle) -> str:
    """The model's input: the question and the facts, both as data.

    The question is placed inside the same untrusted block as the facts rather
    than beside the instructions. It arrived from a browser, so it gets exactly
    the treatment a collected post gets.
    """
    numbered = "\n".join(
        f"- methodology.{index}: {note}" for index, note in enumerate(bundle.methodology_notes)
    )
    return (
        f"QUESTION FROM A SIGNED-IN USER:\n{question}\n\n"
        f"FACTS AVAILABLE:\n{bundle.render()}\n\n"
        f"METHODOLOGY NOTES (citable by id):\n{numbered}"
    )


def _cache_hash(question: str, bundle: FactBundle) -> str:
    """A cache key over the question and the facts together."""
    return hashlib.sha256(f"{bundle.content_hash()}\x00{question}".encode()).hexdigest()
