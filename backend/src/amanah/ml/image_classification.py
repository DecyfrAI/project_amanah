"""Server-side image classification (B-S26.4, ADR 0007).

The pixels never cross the browser API boundary in either direction. A client
names a catalogued example; the server reads the bytes from private object
storage, sends them to the model, and returns a classification object. ADR 0007
is explicit that the browser does not send base64 and does not call a vision API,
and the shape of this service is what enforces that.

The staged taxonomy is shared with text classification rather than duplicated. An
image and a comment expressing the same collective blame should receive the same
label, and a second taxonomy for images would drift from the first within a
release.

Dataset annotations stay out. A row's `annotation_*` columns say what the source
dataset claimed; nothing here reads them, so the model cannot be primed by a label
it is supposed to be independently reproducing, and a prediction cannot quietly
become a copy of someone else's ground truth.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.images import ImageClassification
from amanah.domain.enums import (
    ConfidenceTier,
    InferenceStatus,
    PublicPlatform,
    Relevance,
    RetentionPolicy,
    Severity,
    Stance,
)
from amanah.ml.catalog import CLASSIFY_IMAGE_PROMPT, CLASSIFY_IMAGE_PROMPT_ID
from amanah.ml.classification import CALL_CONVENTION_VERSION, NON_ANSWER_SCORE
from amanah.ml.confidence import DEFAULT_THRESHOLDS, ConfidenceThresholds, review_reason
from amanah.ml.gemini import GeminiClient, InferenceRequest, InlineImage
from amanah.ml.policy import DataClass, TransferRequest
from amanah.ml.results import InferenceSuccess, failure_reason
from amanah.ml.taxonomy import ClassificationOutput
from amanah.ml.versions import TAXONOMY_VERSION

logger = logging.getLogger(__name__)

#: Reads one private object's bytes. Injected so this service depends on the
#: *capability* rather than on a particular storage client, and so a test can
#: exercise the real classification path without a bucket.
type ObjectReader = Callable[[str], bytes]


@dataclass(frozen=True, slots=True)
class ImageToClassify:
    """One image to classify, by reference and by digest.

    Exactly one of `image_example_id` and `image_upload_id` is set, mirroring the
    `exactly_one_subject` constraint on the row this produces. The distinction is
    not bookkeeping: a catalogue entry is reviewed corpus material this product
    may send to the provider, while an upload is one person's unreviewed file
    that requires a deployment opt-in first.
    """

    storage_path: str
    sha256: str
    mime_type: str
    image_example_id: UUID | None = None
    image_upload_id: UUID | None = None
    is_fixture: bool = True
    #: The data class this image belongs to for transfer authorization.
    data_class: DataClass = DataClass.collected_text
    #: Whether this deployment permits sending user-supplied media off-site.
    allow_third_party_content_inference: bool = False

    def __post_init__(self) -> None:
        if (self.image_example_id is None) == (self.image_upload_id is None):
            raise ValueError("name exactly one of image_example_id or image_upload_id")


@dataclass(frozen=True, slots=True)
class ImageClassificationRecord:
    """What one image classification wrote."""

    classification_id: UUID
    status: InferenceStatus
    output: ClassificationOutput | None
    confidence_tier: ConfidenceTier
    requires_review: bool
    reason: str | None = None


class ImageClassificationService:
    """Classifies catalogued images through the controlled Gemini boundary."""

    def __init__(
        self,
        session: Session,
        *,
        client: GeminiClient,
        read_object: ObjectReader,
        thresholds: ConfidenceThresholds = DEFAULT_THRESHOLDS,
    ) -> None:
        self._session = session
        self._client = client
        self._read_object = read_object
        self._thresholds = thresholds

    def classify(
        self, image: ImageToClassify, *, requested_by: UUID | None = None
    ) -> ImageClassificationRecord:
        """Read, classify, and persist one image's staged labels."""
        payload = self._read_object(image.storage_path)
        result = self._client.infer(
            InferenceRequest(
                prompt_id=CLASSIFY_IMAGE_PROMPT_ID,
                content=IMAGE_CONTENT_NOTE,
                # The file digest is the cache key: the same bytes under the same
                # prompt and taxonomy are the same inference, whatever the row
                # around them says.
                content_hash=image.sha256,
                transfer=TransferRequest(
                    data_class=image.data_class,
                    # The research corpus is a reviewed internal fixture pack, not
                    # material collected live from a platform (ADR 0007). A user
                    # upload has no platform either — it came from a device.
                    platform=PublicPlatform.not_applicable,
                    retention_policy=RetentionPolicy.indefinite_permitted,
                    is_fixture=image.is_fixture,
                    allow_third_party_content_inference=(image.allow_third_party_content_inference),
                ),
                image=InlineImage(payload=payload, mime_type=image.mime_type),
            ),
            ClassificationOutput,
        )

        if isinstance(result, InferenceSuccess):
            output = result.payload
            tier = self._thresholds.tier_for(output.score)
            needs_review = review_reason(output, tier) is not None
            classification_id = self._upsert(
                image,
                requested_by=requested_by,
                model_name=result.model_name,
                prompt_version=result.prompt_version,
                relevance=output.relevance,
                stance=output.stance,
                hate_types=[hate_type.value for hate_type in output.hate_types],
                severity=int(output.severity),
                narrative_tags=list(output.narrative_tags),
                score=output.score,
                confidence_tier=tier,
                rationale=output.rationale,
                requires_review=needs_review,
                inference_status=InferenceStatus.succeeded,
            )
            return ImageClassificationRecord(
                classification_id=classification_id,
                status=InferenceStatus.succeeded,
                output=output,
                confidence_tier=tier,
                requires_review=needs_review,
            )

        reason = failure_reason(result)
        logger.info("image classification produced no labels", extra={"reason": reason})
        classification_id = self._upsert(
            image,
            requested_by=requested_by,
            model_name=self._client.model_name,
            prompt_version=CLASSIFY_IMAGE_PROMPT.version,
            relevance=Relevance.uncertain,
            stance=Stance.uncertain,
            hate_types=[],
            severity=int(Severity.none),
            narrative_tags=[],
            score=NON_ANSWER_SCORE,
            confidence_tier=ConfidenceTier.low,
            rationale=None,
            requires_review=result.status is InferenceStatus.invalid_output,
            inference_status=result.status,
        )
        return ImageClassificationRecord(
            classification_id=classification_id,
            status=result.status,
            output=None,
            confidence_tier=ConfidenceTier.low,
            requires_review=result.status is InferenceStatus.invalid_output,
            reason=reason,
        )

    def _upsert(
        self,
        image: ImageToClassify,
        *,
        requested_by: UUID | None,
        model_name: str,
        prompt_version: str,
        relevance: Relevance,
        stance: Stance,
        hate_types: list[str],
        severity: int,
        narrative_tags: list[str],
        score: float,
        confidence_tier: ConfidenceTier,
        rationale: str | None,
        requires_review: bool,
        inference_status: InferenceStatus,
    ) -> UUID:
        """Write one classification, idempotently for its version triple."""
        table = cast(Table, ImageClassification.__table__)
        values: dict[str, Any] = {
            "image_example_id": image.image_example_id,
            "image_upload_id": image.image_upload_id,
            "requested_by": requested_by,
            "model_name": model_name,
            "model_version": CALL_CONVENTION_VERSION,
            "prompt_version": prompt_version,
            "taxonomy_version": TAXONOMY_VERSION,
            "relevance": relevance.value,
            "stance": stance.value,
            "hate_types": hate_types,
            "severity": severity,
            "narrative_tags": narrative_tags,
            "score": score,
            "confidence_tier": confidence_tier.value,
            "rationale": rationale,
            "requires_review": requires_review,
            "inference_status": inference_status.value,
            # Safe call metadata only. The digest identifies which bytes were
            # classified without the row holding any of them.
            "metadata": {"source_sha256": image.sha256, "mime_type": image.mime_type},
            "inferred_at": datetime.now(UTC),
        }
        refreshable = {
            table.c[column]: values[column]
            for column in (
                "relevance",
                "stance",
                "hate_types",
                "severity",
                "narrative_tags",
                "score",
                "confidence_tier",
                "rationale",
                "requires_review",
                "inference_status",
                "inferred_at",
            )
        }
        # The conflict target follows the subject: the two unique constraints
        # cover different columns, and naming the wrong one would let a retry
        # insert a duplicate rather than converge.
        constraint = (
            "image_classifications_image_model_prompt_version_unique"
            if image.image_example_id is not None
            else "image_classifications_upload_model_prompt_version_unique"
        )
        statement: Any = (
            insert(table)
            .values(**values)
            .on_conflict_do_update(constraint=constraint, set_=refreshable)
            .returning(table.c.id)
        )
        return cast(UUID, self._session.execute(statement).scalar_one())


#: The text part beside the image. The prompt's content wrapper needs something
#: to hold, and this says what the attached part is without describing it — a
#: description here would be a label the model should be producing on its own.
IMAGE_CONTENT_NOTE = "The attached image is the item to classify."
