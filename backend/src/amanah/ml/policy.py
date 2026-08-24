"""Data-class and transfer authorization, checked before a request is built.

`spec.md` section 11.3 draws a line the rest of this package may not cross: if
policy or source terms do not permit sending content to Gemini, the pipeline uses
a precomputed result or marks inference unavailable. It does not send anyway and
apologise afterwards.

The check runs *before* the prompt is assembled rather than before the socket is
opened. That ordering is the point: text that was never authorized is never
placed into a request object at all, so it cannot leak through a retry, a log
line, or a cache entry written on the way out.

Two rules are stated here as data rather than as prose.

*Platform.* Reddit content may not be used to train a model without explicit
Reddit consent (`spec.md` section 11.3), and the connector stays disabled until
research access is approved. Rather than reasoning about what a provider might
later do with an inference request, this refuses the transfer outright.

*Retention.* A source whose terms require deletion on request has not granted
permission to copy its text into a third party's system, so `delete_on_request`
is refused for source text as well.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from amanah.domain.enums import PublicPlatform, RetentionPolicy


class DataClass(StrEnum):
    """What kind of material a request would carry.

    The classes are ordered by how much of someone else's material leaves the
    system, and each one is authorized separately: a bundle of counts the product
    computed itself is not the same transfer as the text a person wrote.
    """

    #: Numbers and labels this product derived. Carries no source text.
    derived_aggregate = "derived_aggregate"
    #: Publisher-supplied metadata: headline, outlet, canonical URL.
    public_metadata = "public_metadata"
    #: An excerpt the source's licence permits republishing.
    permitted_excerpt = "permitted_excerpt"
    #: Full collected text of a post, comment, or dataset row.
    collected_text = "collected_text"
    #: Text reached through a URL a signed-in person submitted themselves.
    user_submitted_text = "user_submitted_text"


#: Platforms whose terms do not permit sending their content to a third-party
#: model. Reddit is here per `spec.md` section 11.3 and stays here until an
#: explicit consent decision says otherwise.
BLOCKED_TRANSFER_PLATFORMS: frozenset[PublicPlatform] = frozenset({PublicPlatform.reddit})

#: Retention policies under which source *text* may not be transferred. Metadata
#: and derived aggregates are unaffected: neither is the source's material.
BLOCKED_TRANSFER_RETENTION: frozenset[RetentionPolicy] = frozenset(
    {RetentionPolicy.delete_on_request}
)

#: Classes that carry someone else's words and are therefore subject to the
#: platform and retention rules above.
_SOURCE_TEXT_CLASSES: frozenset[DataClass] = frozenset(
    {DataClass.permitted_excerpt, DataClass.collected_text, DataClass.user_submitted_text}
)


@dataclass(frozen=True, slots=True)
class TransferRequest:
    """What is about to be sent, and where it came from."""

    data_class: DataClass
    platform: PublicPlatform
    retention_policy: RetentionPolicy
    is_fixture: bool = False


@dataclass(frozen=True, slots=True)
class TransferDecision:
    """Whether the transfer may proceed, and a safe reason when it may not.

    `reason` is a stable code rather than a sentence: it is stored on a blocked
    prediction and shown in a run summary, and neither place should carry prose
    that a later policy change would silently make wrong.
    """

    is_permitted: bool
    reason: str | None = None


def authorize_transfer(request: TransferRequest) -> TransferDecision:
    """Decide whether this material may be sent to the model provider.

    A fixture is always permitted: synthetic or redacted records are this
    product's own material, and refusing them would leave the offline pipeline
    unable to prove that the online one works.
    """
    if request.is_fixture:
        return TransferDecision(is_permitted=True)

    if request.data_class not in _SOURCE_TEXT_CLASSES:
        return TransferDecision(is_permitted=True)

    if request.platform in BLOCKED_TRANSFER_PLATFORMS:
        return TransferDecision(is_permitted=False, reason="platform_transfer_not_permitted")

    if request.retention_policy in BLOCKED_TRANSFER_RETENTION:
        return TransferDecision(is_permitted=False, reason="retention_transfer_not_permitted")

    return TransferDecision(is_permitted=True)
