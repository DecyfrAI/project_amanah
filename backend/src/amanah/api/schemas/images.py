"""`GET /v1/image-examples` and `POST /v1/image-classifications` (spec §13.2, v2.2).

Matches `ImageExampleListSchema` and `ImageClassificationSchema` in
`apps/web/src/api/contracts.ts`.

Two absences are the contract, not omissions. There is no field for image bytes,
and there is no field for a durable storage path — a reader receives a short-lived
signed URL and nothing that outlives it (ADR 0007). And a dataset annotation is
its own nested object rather than being merged into the prediction fields, so a
label that shipped with someone else's dataset can never be read as a finding this
product made.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import (
    ConfidenceTier,
    DataMode,
    HateType,
    Relevance,
    Severity,
    Stance,
)

#: Shown beside every classification. `spec.md` section 9.2 requires "classified
#: as likely", never "is hate", and putting it in the payload means a client
#: cannot render the label without it.
IMAGE_CLASSIFICATION_DISCLOSURE = (
    "Classified as likely by an automated model and not yet reviewed by a person. "
    "Dataset annotations are the source dataset's own labels, not Amanah findings."
)


class DatasetAnnotation(ResponseModel):
    """What the source dataset said about this image.

    Provenance about that dataset. Never an Amanah prediction and never a human
    review decision.
    """

    hate_types: list[HateType] = Field(default_factory=list)
    severity: Severity | None = None
    note: str = ""


class ImageExampleEntry(ResponseModel):
    """One catalogued image, with a link that expires."""

    id: UUID
    title: str
    image_url: str = Field(description="Short-lived signed URL. Expires; never store it.")
    image_url_expires_at: UtcDatetime
    alt_text: str = Field(min_length=1)
    form_note: str = ""
    dataset_annotation: DatasetAnnotation
    #: The current model classification, absent when the image has not been
    #: classified. Absence means "not analysed", never "found to be safe".
    relevance: Relevance | None = None
    stance: Stance | None = None
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier | None = None
    narrative_tags: list[str] = Field(default_factory=list)
    rationale: str | None = None


class ImageManifest(ResponseModel):
    """Provenance of the datapack this catalog was imported from."""

    dataset_provider: str
    dataset_name: str
    dataset_version: str
    license_identifier: str
    schema_mapping_version: str
    approval_state: str
    reviewer: str


class ImageExampleListResponse(ResponseModel):
    """`GET /v1/image-examples` payload."""

    data_mode: DataMode
    manifest: ImageManifest | None
    items: list[ImageExampleEntry] = Field(default_factory=list)
    disclosure: str = IMAGE_CLASSIFICATION_DISCLOSURE
    meta: ResponseMeta


class ImageClassificationRequest(RequestModel):
    """Ask for one catalogued image to be classified server-side.

    The client names an example; it does not upload pixels. ADR 0007 keeps image
    bytes off this boundary in both directions.
    """

    example_id: UUID


class ImageClassificationResponse(ResponseModel):
    """`POST /v1/image-classifications` payload.

    `status` is a fixed literal because there is only one state a fresh
    classification can be in. A reviewed image is a different surface, and
    hard-coding this value stops a client from ever rendering an unreviewed
    label as a confirmed one.
    """

    example_id: UUID
    data_mode: DataMode
    relevance: Relevance
    stance: Stance
    hate_types: list[HateType] = Field(default_factory=list)
    severity: Severity | None = None
    narrative_tags: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    rationale: str = ""
    model_name: str
    model_version: str
    taxonomy_version: str
    review_required: bool
    dataset_annotation: DatasetAnnotation | None = None
    status: str = "classified_not_reviewed"
    disclosure: str = IMAGE_CLASSIFICATION_DISCLOSURE
    meta: ResponseMeta
