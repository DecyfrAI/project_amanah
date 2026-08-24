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
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import Row

from amanah.api.ai import GeminiDependency
from amanah.api.dependencies import CurrentUser, DatabaseSession, build_response_meta, get_settings
from amanah.api.errors import ApiError, ResourceNotFoundError, ServiceUnavailableError
from amanah.api.schemas.errors import ErrorCode
from amanah.api.schemas.images import (
    DatasetAnnotation,
    ImageClassificationRequest,
    ImageClassificationResponse,
    ImageExampleEntry,
    ImageExampleListResponse,
    ImageManifest,
    ImageUploadResponse,
)
from amanah.db.repositories.images import ImageCatalogRepository
from amanah.domain.enums import ConfidenceTier, HateType, Relevance, Severity, Stance
from amanah.images.cleaning import ImageRejectedError, clean_image, read_bounded_upload
from amanah.images.uploads import ImageUploadService
from amanah.ingestion.contract import AdapterError
from amanah.ml.classification import CALL_CONVENTION_VERSION
from amanah.ml.image_classification import ImageClassificationService, ImageToClassify
from amanah.ml.policy import DataClass
from amanah.ml.versions import TAXONOMY_VERSION
from amanah.settings import Settings
from amanah.storage.object_store import ObjectStore, build_object_reader
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
        try:
            signed = signer.sign(path)
        except AdapterError as exc:
            # Signing is a provider call now, so it can fail per object. One
            # refused link must not fail the whole catalogue, and it must not
            # degrade into an unsigned one.
            logger.warning(
                "image example could not be signed",
                extra={"example_id": str(row.id), "reason": exc.safe_code},
            )
            continue
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


@router.post(
    "/image-uploads",
    summary="Upload one image for classification",
    status_code=status.HTTP_201_CREATED,
)
def upload_image(
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="One JPEG, PNG, or WebP image.")],
) -> ImageUploadResponse:
    """Clean, store, and record one image the caller uploaded (B-S28).

    Nothing the client sent about the file is trusted. The byte cap is enforced
    while reading rather than from the declared length, the format is decided by
    decoding the bytes rather than from the filename or content type, and the
    stored object is a re-encode — so EXIF, GPS, and any trailing non-image
    payload do not survive. The storage key is generated server-side.

    Classification is a separate call. A model failure therefore never costs the
    person their upload.
    """
    try:
        store = ObjectStore.from_settings(settings)
    except SigningUnavailableError as exc:
        logger.warning("image upload refused", extra={"reason": "storage_not_configured"})
        raise ServiceUnavailableError("Image upload is not available in this environment.") from exc

    try:
        raw = read_bounded_upload(file.file, max_bytes=settings.image_upload_max_bytes)
        cleaned = clean_image(
            raw,
            max_pixels=settings.image_upload_max_pixels,
            max_dimension=settings.image_upload_max_dimension,
        )
    except ImageRejectedError as exc:
        raise _rejected(exc, settings) from exc
    finally:
        file.file.close()

    service = ImageUploadService(
        session, store=store, retention_days=settings.image_upload_retention_days
    )
    stored = service.store(cleaned, owner_user_id=user.user_id)

    upload = service.get_owned(stored.upload_id, owner_user_id=user.user_id)
    signed = ObjectUrlSigner.from_settings(settings).sign(
        upload.storage_path if upload is not None else ""
    )
    return ImageUploadResponse(
        upload_id=stored.upload_id,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
        pixel_width=stored.pixel_width,
        pixel_height=stored.pixel_height,
        sha256=stored.sha256,
        is_new=stored.is_new,
        retention_expires_at=upload.retention_expires_at if upload is not None else None,
        image_url=signed.url,
        image_url_expires_at=signed.expires_at,
        meta=build_response_meta(settings),
    )


@router.post("/image-classifications", summary="Classify one catalogued or uploaded image")
def classify_image(
    body: ImageClassificationRequest,
    user: CurrentUser,
    session: DatabaseSession,
    client: GeminiDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageClassificationResponse:
    """Classify one image through the controlled Gemini boundary.

    The caller names a published catalogue example or one of its own uploads, and
    the server fetches the bytes. Pixels never cross this boundary in either
    direction (ADR 0007); an upload arrives through `POST /v1/image-uploads`.
    """
    repository = ImageCatalogRepository(session)
    try:
        read_object = build_object_reader(settings)
    except SigningUnavailableError as exc:
        # No Storage credential, so the bytes cannot be fetched. Reporting this
        # as unavailable is the honest answer; the alternative would be a
        # classification of nothing.
        logger.warning("image classification refused", extra={"reason": "storage_not_configured"})
        raise ServiceUnavailableError(
            "Image analysis is not available in this environment."
        ) from exc

    # The request model guarantees exactly one of these is set; re-reading them
    # here keeps that visible to a reader and to the type checker.
    if body.example_id is not None:
        subject = _catalogue_subject(repository, body.example_id)
    elif body.upload_id is not None:
        subject = _upload_subject(session, settings, body.upload_id, owner_user_id=user.user_id)
    else:  # pragma: no cover - the request validator rejects this first
        raise ApiError(
            code=ErrorCode.validation_failed,
            status_code=422,
            message="Name exactly one of example_id or upload_id.",
        )

    service = ImageClassificationService(session, client=client, read_object=read_object)
    record = service.classify(subject, requested_by=user.user_id)
    if record.output is None:
        # The model produced nothing usable. `spec.md` section 11.2 keeps the
        # rest of the product working and marks the analysis unavailable.
        raise ServiceUnavailableError(
            "Image analysis is unavailable right now. The stored image is unchanged."
        )

    catalog_row = repository.get_example(body.example_id) if body.example_id is not None else None
    output = record.output
    return ImageClassificationResponse(
        example_id=body.example_id,
        upload_id=body.upload_id,
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


def _catalogue_subject(repository: ImageCatalogRepository, example_id: UUID) -> ImageToClassify:
    """A reviewed corpus image. Permitted material under ADR 0007."""
    target = repository.read_storage_target(example_id)
    if target is None:
        raise ResourceNotFoundError("No published image example was found for that id.")
    return ImageToClassify(
        image_example_id=target.id,
        storage_path=target.storage_path,
        sha256=target.sha256,
        mime_type=target.mime_type,
        data_class=DataClass.collected_text,
    )


def _upload_subject(
    session: DatabaseSession,
    settings: Settings,
    upload_id: UUID,
    *,
    owner_user_id: UUID,
) -> ImageToClassify:
    """One of the caller's own uploads.

    Ownership is re-checked here rather than assumed from the identifier: a
    `upload_id` is a client-supplied value, and reading someone else's private
    file is exactly what this route must not allow. A missing row and a row
    belonging to another user produce the same `404`, so the response cannot be
    used to discover which identifiers exist.
    """
    store = ObjectStore.from_settings(settings)
    service = ImageUploadService(session, store=store)
    upload = service.get_owned(upload_id, owner_user_id=owner_user_id)
    if upload is None:
        raise ResourceNotFoundError("No upload of yours was found for that id.")

    return ImageToClassify(
        image_upload_id=upload.id,
        storage_path=upload.storage_path,
        sha256=upload.sha256,
        mime_type=upload.mime_type,
        # An upload is never fixture material, whatever the deployment's data
        # mode says: it is one person's own file.
        is_fixture=False,
        data_class=DataClass.user_submitted_media,
        allow_third_party_content_inference=settings.allow_third_party_content_inference,
    )


def _rejected(error: ImageRejectedError, settings: Settings) -> ApiError:
    """Map a refusal onto a safe, actionable message.

    The wording describes the *limit*, never the file: telling a sender what was
    detected in their upload would turn this endpoint into an oracle.
    """
    megabytes = settings.image_upload_max_bytes // (1024 * 1024)
    messages = {
        "image_too_large": f"That image is larger than the {megabytes} MB limit.",
        "image_empty": "That file was empty.",
        "image_format_not_allowed": "Upload a JPEG, PNG, or WebP image.",
        "image_unreadable": "That file could not be read as an image.",
        "image_dimensions_too_large": (
            f"That image is wider or taller than {settings.image_upload_max_dimension} pixels."
        ),
        "image_too_many_pixels": "That image has too many pixels to process.",
    }
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=413 if error.code == "image_too_large" else 422,
        message=messages.get(error.code, "That file could not be accepted."),
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
