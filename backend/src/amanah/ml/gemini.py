"""The one boundary that talks to Gemini (B-S13).

Everything in this module exists to make a single guarantee: no material reaches
the provider that policy, budget, or schema did not clear first, and nothing comes
back that has not been validated into a declared Pydantic model.

The order of the checks is the design, not an implementation detail:

1. **Prompt lookup.** An unregistered prompt id fails before anything else, so an
   ad-hoc instruction string cannot reach the provider.
2. **Data class.** The registered prompt declares what it may carry; a caller
   passing the wrong material is refused here rather than at review time.
3. **Transfer authorization.** `spec.md` section 11.3 — refused material is never
   placed into a request object at all.
4. **Cache.** A hit costs nothing and spends no budget.
5. **Budget.** Reserved before the call, reconciled after it.
6. **Truncation.** Input is cut to the configured character cap, so one oversized
   item cannot consume a run's budget.
7. **Call, then validate.** The response is parsed into the prompt's declared
   model. Anything else is `invalid_output`, which routes to human review.

The provider is reached through `amanah.ingestion.http`, the same bounded
transport every other outbound call uses, so timeouts and the response byte
budget cannot drift between Gemini and the news adapters.

No tool declarations, no function calling, no grounding, no file API. `spec.md`
section 11.3 requires Gemini to have no arbitrary SQL, network, publishing,
reporting, or identity-search tool, and the way to guarantee that is to never
send a `tools` field.
"""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from amanah.ingestion.contract import AdapterError
from amanah.ingestion.http import ClientFactory, HttpLimits, http_client, request_bounded
from amanah.ml.budgets import TokenBudget, estimate_tokens
from amanah.ml.cache import InferenceCache, inference_cache_key
from amanah.ml.policy import TransferRequest, authorize_transfer
from amanah.ml.prompts import PromptDefinition, PromptRegistry
from amanah.ml.results import (
    InferenceDeferred,
    InferenceFailure,
    InferenceInvalidOutput,
    InferencePolicyBlocked,
    InferenceProviderFailure,
    InferenceResult,
    InferenceSuccess,
    InferenceUsage,
    describe,
)
from amanah.ml.versions import INFERENCE_VERSION, TAXONOMY_VERSION
from amanah.settings import Settings

logger = logging.getLogger(__name__)

API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

#: Deterministic decoding. A classifier that returns a different label for the
#: same text on two runs cannot be evaluated, and `rules/ml.md` requires seeded,
#: reproducible inference.
GENERATION_TEMPERATURE = 0.0

#: Statuses worth one more attempt. Everything else is a permanent answer, and
#: retrying it only spends the budget before an operator sees the code.
_RETRYABLE_PROVIDER_CODES = frozenset(
    {"provider_timeout", "provider_unreachable", "provider_unavailable", "provider_request_failed"}
)

#: Provider codes that mean "not permitted" rather than "did not work".
_POLICY_PROVIDER_CODES = frozenset({"provider_access_required"})

#: Budget charge for one inline image. A flat, deliberately generous figure: the
#: provider prices an image at a fixed rate for the sizes this corpus holds, and
#: a budget guard should over-reserve rather than under-reserve.
IMAGE_TOKEN_ESTIMATE = 1600


@dataclass(frozen=True, slots=True)
class InlineImage:
    """Image bytes for one call, carried as a distinct part.

    Separate from `content` because an image is not text. Base64-encoding it into
    the text part would hand the model a very long string instead of a picture,
    and would be silently truncated by the input character cap. Encoding happens
    at the request boundary and the result is never stored, logged, or returned —
    ADR 0007 keeps pixels out of the database and out of every response.
    """

    payload: bytes
    mime_type: str

    def estimated_tokens(self) -> int:
        """A flat cost for one image.

        The provider bills an image at a fixed rate for the sizes this corpus
        holds, so a per-byte estimate would model the wrong thing. Deliberately
        generous, because the budget's job is to fail safe.
        """
        return IMAGE_TOKEN_ESTIMATE


@dataclass(frozen=True, slots=True)
class InferenceRequest:
    """One classification or summarisation call, fully described.

    `content_hash` is supplied by the caller rather than computed here: the
    canonical pipeline already hashes every item, and re-hashing the rendered
    prompt would produce a key that changes whenever formatting changes, which is
    exactly the cache invalidation this design avoids.
    """

    prompt_id: str
    content: str
    content_hash: str
    transfer: TransferRequest
    image: InlineImage | None = None


class GeminiClient:
    """Policy-gated, budgeted, schema-validated access to one Gemini model.

    Not configured is a first-class state. When no API key or model name is set
    the client is constructed anyway and every call returns `deferred`, so the
    pipeline runs end to end without AI and the rest of the product keeps working
    (`spec.md` section 11.2).
    """

    def __init__(
        self,
        *,
        settings: Settings,
        registry: PromptRegistry,
        budget: TokenBudget,
        cache: InferenceCache | None = None,
        client_factory: ClientFactory = http_client,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._budget = budget
        self._cache = cache if cache is not None else InferenceCache()
        self._client_factory = client_factory
        self._limits = HttpLimits(
            connect_timeout_seconds=settings.http_connect_timeout_seconds,
            read_timeout_seconds=settings.gemini_timeout_seconds,
            total_timeout_seconds=settings.gemini_timeout_seconds,
            max_response_bytes=settings.http_max_response_bytes,
        )

    @property
    def is_configured(self) -> bool:
        """Whether a key and a model name are both present."""
        return self._settings.gemini_api_key is not None and bool(self._settings.gemini_model)

    @property
    def model_name(self) -> str:
        """The configured model, or a stable placeholder when unconfigured.

        Recorded on deferred predictions so a row still says which model *would*
        have produced it, without inventing a name that was never configured.
        """
        return self._settings.gemini_model or "unconfigured"

    def infer[PayloadT: BaseModel](
        self, request: InferenceRequest, response_model: type[PayloadT]
    ) -> InferenceResult[PayloadT]:
        """Run one gated, budgeted, validated inference."""
        prompt = self._registry.get(request.prompt_id)
        if prompt.response_model is not response_model:
            # A caller asking for a model the prompt does not produce would get
            # validation failures that look like provider faults. Refuse instead.
            raise ValueError(
                f"prompt {prompt.prompt_id} does not produce {response_model.__name__}"
            )

        gate = self._gate(request, prompt)
        if gate is not None:
            return gate

        key = inference_cache_key(
            content_hash=request.content_hash,
            model_name=self.model_name,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            taxonomy_version=TAXONOMY_VERSION,
            inference_version=INFERENCE_VERSION,
        )
        cached = self._cache.get(key)
        if isinstance(cached, response_model):
            return InferenceSuccess(
                payload=cached,
                model_name=self.model_name,
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                was_cached=True,
            )

        content = request.content[: self._settings.gemini_max_input_characters]
        body = self._build_request_body(prompt, content, response_model, request.image)
        estimated = estimate_tokens(prompt.render_system()) + estimate_tokens(content)
        if request.image is not None:
            estimated += request.image.estimated_tokens()

        grant = self._budget.request(estimated)
        if not grant.is_granted:
            logger.info("inference deferred", extra={"reason": grant.reason})
            return InferenceDeferred(reason=grant.reason or "budget_exhausted")

        result = self._call_with_retries(prompt, body, response_model, estimated)
        if isinstance(result, InferenceSuccess):
            self._cache.set(key, result.payload)
        logger.info("inference completed", extra=describe(result))
        return result

    def _gate(self, request: InferenceRequest, prompt: PromptDefinition) -> InferenceFailure | None:
        """Every refusal that must happen before a request body exists."""
        if not self.is_configured:
            return InferenceDeferred(reason="gemini_not_configured")

        if request.transfer.data_class not in prompt.permitted_data_classes:
            logger.warning(
                "inference refused",
                extra={
                    "reason": "data_class_not_permitted",
                    "prompt_id": prompt.prompt_id,
                    "data_class": request.transfer.data_class.value,
                },
            )
            return InferencePolicyBlocked(reason="data_class_not_permitted")

        decision = authorize_transfer(request.transfer)
        if not decision.is_permitted:
            logger.warning(
                "inference refused",
                extra={"reason": decision.reason, "prompt_id": prompt.prompt_id},
            )
            return InferencePolicyBlocked(reason=decision.reason or "transfer_not_permitted")
        return None

    def _build_request_body(
        self,
        prompt: PromptDefinition,
        content: str,
        response_model: type[BaseModel],
        image: InlineImage | None,
    ) -> dict[str, Any]:
        """Assemble the request.

        The system instruction and the content occupy different fields of the
        payload; they are never concatenated. An image travels as its own
        `inlineData` part rather than encoded into the text, so the model receives
        a picture and the input character cap does not truncate it into garbage.

        `responseSchema` asks the provider to constrain its own decoding, and the
        reply is still validated locally — a provider-side constraint is a
        convenience, not a guarantee this code may depend on.
        """
        parts: list[dict[str, Any]] = [{"text": prompt.render_content(content)}]
        if image is not None:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": image.mime_type,
                        "data": base64.b64encode(image.payload).decode("ascii"),
                    }
                }
            )
        return {
            "systemInstruction": {"parts": [{"text": prompt.render_system()}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": GENERATION_TEMPERATURE,
                "maxOutputTokens": self._settings.gemini_max_output_tokens,
                "responseMimeType": "application/json",
                "responseSchema": _to_provider_schema(response_model),
            },
        }

    def _call_with_retries[PayloadT: BaseModel](
        self,
        prompt: PromptDefinition,
        body: Mapping[str, Any],
        response_model: type[PayloadT],
        estimated: int,
    ) -> InferenceResult[PayloadT]:
        """Send, retrying only transient transport failures.

        An invalid output is never retried. The call is deterministic
        (`temperature` 0), so a second identical request produces the same
        unparseable answer and spends the budget to learn nothing.
        """
        attempts = self._settings.gemini_max_retries + 1
        last: InferenceResult[PayloadT] = InferenceProviderFailure(
            safe_code="provider_unreachable", is_retryable=True
        )
        for attempt in range(attempts):
            last = self._call_once(prompt, body, response_model, estimated)
            if not isinstance(last, InferenceProviderFailure) or not last.is_retryable:
                return last
            if attempt < attempts - 1:
                logger.info(
                    "retrying inference",
                    extra={"attempt": attempt + 1, "safe_code": last.safe_code},
                )
        return last

    def _call_once[PayloadT: BaseModel](
        self,
        prompt: PromptDefinition,
        body: Mapping[str, Any],
        response_model: type[PayloadT],
        estimated: int,
    ) -> InferenceResult[PayloadT]:
        try:
            document = self._post(body)
        except AdapterError as exc:
            self._budget.release(estimated)
            if exc.safe_code in _POLICY_PROVIDER_CODES or exc.is_policy_block:
                return InferencePolicyBlocked(reason="provider_access_required")
            return InferenceProviderFailure(
                safe_code=exc.safe_code,
                is_retryable=exc.safe_code in _RETRYABLE_PROVIDER_CODES,
            )

        usage = _read_usage(document)
        self._budget.reconcile(estimated_tokens=estimated, actual_tokens=usage.total_tokens)

        text = _read_output_text(document)
        if text is None:
            return InferenceInvalidOutput(reason="provider_returned_no_content")
        try:
            payload = response_model.model_validate_json(text)
        except ValidationError:
            # The offending text is not logged: it is model output derived from
            # source material and can echo it back verbatim.
            logger.warning(
                "inference output failed schema validation",
                extra={"prompt_id": prompt.prompt_id},
            )
            return InferenceInvalidOutput(reason="output_failed_schema_validation")

        return InferenceSuccess(
            payload=payload,
            model_name=self.model_name,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            usage=usage,
        )

    def _post(self, body: Mapping[str, Any]) -> Mapping[str, Any]:
        """One bounded HTTPS call. Raises `AdapterError` on any transport fault."""
        api_key = self._settings.gemini_api_key
        if api_key is None:
            raise AdapterError("gemini_not_configured", is_retryable=False)

        url = f"{API_BASE_URL}/models/{self.model_name}:generateContent"
        with self._client_factory(self._limits) as client:
            response = request_bounded(
                client,
                "POST",
                url,
                limits=self._limits,
                # The key travels in a header rather than the query string, so it
                # cannot be captured by proxy access logs that record URLs.
                headers={
                    "x-goog-api-key": api_key.get_secret_value(),
                    "Content-Type": "application/json",
                },
                json_body=dict(body),
            )

        if response.status_code == 429:
            raise AdapterError("provider_rate_limited", is_retryable=True)
        if response.status_code in {401, 403}:
            raise AdapterError("provider_access_required", is_policy_block=True)
        if response.status_code >= 500:
            raise AdapterError("provider_unavailable", is_retryable=True)
        if response.status_code >= 400:
            raise AdapterError("provider_rejected_request", is_retryable=False)

        try:
            document = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise AdapterError("provider_response_malformed", is_retryable=False) from exc
        if not isinstance(document, dict):
            raise AdapterError("provider_response_malformed", is_retryable=False)
        return document


#: One node of a decoded JSON document. Spelled out rather than using `Any` so
#: the schema walkers below stay type-checked instead of opting out.
type JsonNode = str | int | float | bool | list["JsonNode"] | dict[str, "JsonNode"] | None


def _to_provider_schema(model: type[BaseModel]) -> dict[str, JsonNode]:
    """Reduce a Pydantic JSON schema to what the provider accepts.

    `$defs`/`$ref` indirection and the annotation keywords Pydantic emits are not
    part of the provider's schema dialect, so the schema is inlined and pruned.
    Local validation is unaffected: this only shapes the hint sent upstream.
    """
    schema: dict[str, JsonNode] = model.model_json_schema(ref_template="{model}")
    definitions = schema.pop("$defs", {})
    inlined = _inline(schema, definitions if isinstance(definitions, dict) else {})
    pruned = _prune(inlined)
    return pruned if isinstance(pruned, dict) else {}


def _inline(node: JsonNode, definitions: Mapping[str, JsonNode]) -> JsonNode:
    """Replace every `$ref` with the definition it names."""
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str):
            target = definitions.get(reference)
            return _inline(target, definitions) if isinstance(target, dict) else {}
        return {key: _inline(value, definitions) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline(item, definitions) for item in node]
    return node


#: Keywords the provider's schema dialect does not accept. Dropping them narrows
#: the hint, never the local validation that follows.
_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {"title", "default", "additionalProperties", "exclusiveMinimum", "exclusiveMaximum", "$schema"}
)


def _prune(node: JsonNode) -> JsonNode:
    """Drop keywords the provider's schema dialect rejects."""
    if isinstance(node, dict):
        return {
            key: _prune(value)
            for key, value in node.items()
            if key not in _UNSUPPORTED_SCHEMA_KEYWORDS
        }
    if isinstance(node, list):
        return [_prune(item) for item in node]
    return node


def _read_output_text(document: Mapping[str, object]) -> str | None:
    """Pull the text parts out of the first candidate.

    Every absent or unexpected shape returns `None` rather than raising: a
    truncated or filtered response is a normal provider outcome, and the caller
    already has an `invalid_output` state that routes it to review.
    """
    candidates = document.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    first = candidates[0]
    if not isinstance(first, dict):
        return None
    content = first.get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return None
    texts = [str(part["text"]) for part in parts if isinstance(part, dict) and "text" in part]
    return "".join(texts) or None


def _read_usage(document: Mapping[str, object]) -> InferenceUsage:
    """Read reported token usage, defaulting to zero when absent."""
    metadata = document.get("usageMetadata")
    if not isinstance(metadata, dict):
        return InferenceUsage()
    return InferenceUsage(
        prompt_tokens=_as_count(metadata.get("promptTokenCount")),
        output_tokens=_as_count(metadata.get("candidatesTokenCount")),
    )


def _as_count(value: object) -> int:
    """A non-negative integer count, or zero for anything else."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
