"""`GET /v1/image-examples` and `POST /v1/image-classifications` (ADR 0007).

Both routes are authenticated by the `/v1` router, so anonymous access is denied
before either handler runs. Neither returns image bytes: the catalog returns
short-lived signed URLs, and classification returns labels for an example the
caller named by id.

Object storage is reached server-side. When no signing key is configured the
catalog reports itself unavailable rather than serving unsigned, permanent links.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import Row

from amanah.api.ai import GeminiDependency
from amanah.api.dependencies import CurrentUser, DatabaseSession, build_response_meta, get_settings
from amanah.api.errors import ResourceNotFoundError, ServiceUnavailableError
from amanah.api.schemas.images import (
    DatasetAnnotation,
    ImageClassificationRequest,
    ImageClassificationResponse,
    ImageExampleEntry,
    ImageExampleListResponse,
    ImageManifest,
)
from amanah.db.repositories.images import ImageCatalogRepository
from amanah.domain.enums import ConfidenceTier, HateType, Relevance, Severity, Stance
from amanah.ml.classification import CALL_CONVENTION_VERSION
from amanah.ml.image_classification import ImageClassificationService, ImageToClassify
from amanah.ml.versions import TAXONOMY_VERSION
from amanah.settings import Settings
from amanah.storage.object_store import build_object_reader
from amanah.storage.signed_urls import ObjectUrlSigner, SigningUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])


@router.get("/image-examples", summary="Read the authenticated image-evidence catalog")
def list_image_examples(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageExampleListResponse:
    """Return published catalog entries with links that expire."""
    try:
        signer = ObjectUrlSigner.from_settings(settings)
    except SigningUnavailableError as exc:
        # An unsigned link would be a permanent public one. Refuse instead.
        logger.warning("image catalog refused", extra={"reason": "signing_unavailable"})
        raise ServiceUnavailableError(
            "The image catalog is not available in this environment."
        ) from exc

    repository = ImageCatalogRepository(session)
    rows = repository.list_examples()
    paths = repository.read_storage_paths(tuple(row.id for row in rows))

    items: list[ImageExampleEntry] = []
    for row in rows:
        path = paths.get(row.id)
        if path is None:
            # A catalogued row whose object is missing is a curation fault, not
            # something to paper over with a broken link.
            logger.warning("image example has no storage path", extra={"example_id": str(row.id)})
            continue
        signed = signer.sign(path)
        items.append(
            ImageExampleEntry(
                id=row.id,
                title=row.title,
                image_url=signed.url,
                image_url_expires_at=signed.expires_at,
                alt_text=row.alt_text,
                form_note=row.form_note or "",
                dataset_annotation=_dataset_annotation(row),
                relevance=_optional_enum(Relevance, row.relevance),
                stance=_optional_enum(Stance, row.stance),
                score=row.score,
                confidence_tier=_optional_enum(ConfidenceTier, row.confidence_tier),
                narrative_tags=[str(tag) for tag in (row.narrative_tags or ())],
                rationale=row.rationale,
            )
        )

    return ImageExampleListResponse(
        data_mode=settings.data_mode,
        manifest=_manifest(rows[0]) if rows else None,
        items=items,
        meta=build_response_meta(settings),
    )


@router.post("/image-classifications", summary="Classify one catalogued image server-side")
def classify_image(
    body: ImageClassificationRequest,
    user: CurrentUser,
    session: DatabaseSession,
    client: GeminiDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageClassificationResponse:
    """Classify one published example through the controlled Gemini boundary.

    The caller names an example; the server fetches the bytes. Pixels never cross
    this boundary in either direction (ADR 0007).
    """
    repository = ImageCatalogRepository(session)
    target = repository.read_storage_target(body.example_id)
    if target is None:
        raise ResourceNotFoundError("No published image example was found for that id.")

    service = ImageClassificationService(
        session,
        client=client,
        read_object=build_object_reader(settings),
    )
    record = service.classify(
        ImageToClassify(
            image_example_id=target.id,
            storage_path=target.storage_path,
            sha256=target.sha256,
            mime_type=target.mime_type,
        ),
        requested_by=user.user_id,
    )
    if record.output is None:
        # The model produced nothing usable. `spec.md` section 11.2 keeps the
        # rest of the product working and marks the analysis unavailable.
        raise ServiceUnavailableError(
            "Image analysis is unavailable right now. The catalog entry is unchanged."
        )

    catalog_row = repository.get_example(body.example_id)
    output = record.output
    return ImageClassificationResponse(
        example_id=body.example_id,
        data_mode=settings.data_mode,
        relevance=output.relevance,
        stance=output.stance,
        hate_types=list(output.hate_types),
        severity=output.severity,
        narrative_tags=list(output.narrative_tags),
        score=output.score,
        confidence_tier=record.confidence_tier,
        rationale=output.rationale,
        model_name=client.model_name,
        model_version=CALL_CONVENTION_VERSION,
        taxonomy_version=TAXONOMY_VERSION,
        review_required=record.requires_review,
        dataset_annotation=(_dataset_annotation(catalog_row) if catalog_row is not None else None),
        meta=build_response_meta(settings),
    )


def _dataset_annotation(row: Row[Any]) -> DatasetAnnotation:
    """The source dataset's own labels, kept separate from any prediction."""
    return DatasetAnnotation(
        hate_types=[HateType(value) for value in (row.annotation_hate_types or ())],
        severity=(
            Severity(row.annotation_severity) if row.annotation_severity is not None else None
        ),
        note=row.annotation_note or "",
    )


def _manifest(row: Row[Any]) -> ImageManifest:
    """Provenance of the datapack behind the catalog.

    Read from the first row because every published entry in this corpus comes
    from one reviewed pack. A second pack would make this a per-entry field, and
    the projection already carries the columns for that.
    """
    return ImageManifest(
        dataset_provider=row.dataset_provider,
        dataset_name=row.dataset_name,
        dataset_version=row.dataset_version,
        license_identifier=row.dataset_license_id,
        schema_mapping_version=row.dataset_schema_mapping_version,
        approval_state=row.dataset_approval_status,
        reviewer=row.dataset_reviewer or "unattributed",
    )


def _optional_enum[EnumT: StrEnum](enum_type: type[EnumT], value: str | None) -> EnumT | None:
    """Parse a projected enum label, or report it absent.

    Absent means the image has not been classified. It never means the image was
    found to be safe.
    """
    return enum_type(value) if value else None
