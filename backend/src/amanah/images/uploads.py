"""Storing an authenticated user's image upload (B-S28).

The order of operations is the interesting part. Bytes are cleaned first, then
written to object storage, then recorded in PostgreSQL — and if the database
write fails, the object is removed again. The alternative orderings both leave
something worse behind: a row pointing at an object that was never written, or
an object nothing references and nothing will ever clean up.

The storage key is generated here and never derived from anything the caller
sent. A path built from a filename is a path traversal waiting to happen, and a
path built from the digest would leak that two users hold the same picture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from amanah.db.models.images import ImageUpload
from amanah.images.cleaning import CleanedImage
from amanah.ingestion.contract import AdapterError
from amanah.storage.object_store import ObjectStore

logger = logging.getLogger(__name__)

#: Extension per stored media type. Cosmetic — the object is addressed by key —
#: but it makes a bucket listing readable during an incident.
_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

#: Prefix separating user uploads from the reviewed corpus inside the bucket.
UPLOAD_PREFIX = "user-images"


@dataclass(frozen=True, slots=True)
class StoredUpload:
    """The row that now exists, and whether this call created it."""

    upload_id: UUID
    sha256: str
    mime_type: str
    byte_size: int
    pixel_width: int
    pixel_height: int
    is_new: bool


class ImageUploadService:
    """Cleans, stores, and records one uploaded image."""

    def __init__(self, session: Session, *, store: ObjectStore, retention_days: int = 30) -> None:
        self._session = session
        self._store = store
        self._retention_days = retention_days

    def store(self, cleaned: CleanedImage, *, owner_user_id: UUID) -> StoredUpload:
        """Persist one cleaned image for its owner.

        Re-uploading the same picture converges on the existing row rather than
        writing a second copy: the digest of the *cleaned* bytes is unique per
        owner, so this is idempotent for the natural key without needing a
        client-supplied idempotency token.
        """
        existing = self._session.execute(
            select(ImageUpload).where(
                ImageUpload.owner_user_id == owner_user_id,
                ImageUpload.sha256 == cleaned.sha256,
                ImageUpload.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing is not None:
            return _to_stored(existing, is_new=False)

        storage_path = self._build_path(owner_user_id, cleaned.mime_type)
        self._store.upload(storage_path, cleaned.payload, mime_type=cleaned.mime_type)

        upload = ImageUpload(
            owner_user_id=owner_user_id,
            storage_bucket=self._store.bucket,
            storage_path=storage_path,
            sha256=cleaned.sha256,
            mime_type=cleaned.mime_type,
            byte_size=cleaned.byte_size,
            pixel_width=cleaned.pixel_width,
            pixel_height=cleaned.pixel_height,
            # The database clock, matching the `created_at` default, so the
            # retention check constraint cannot fail on clock skew.
            retention_expires_at=func.now() + timedelta(days=self._retention_days),
        )
        self._session.add(upload)
        try:
            self._session.commit()
        except Exception:
            # The object is already in the bucket and nothing will reference it.
            # Remove it rather than leaving private bytes nobody can reach or
            # audit.
            self._session.rollback()
            self._remove_quietly(storage_path)
            raise

        self._session.refresh(upload)
        logger.info("image upload stored", extra={"upload_id": str(upload.id)})
        return _to_stored(upload, is_new=True)

    def get_owned(self, upload_id: UUID, *, owner_user_id: UUID) -> ImageUpload | None:
        """One upload, only if this caller owns it and it still exists."""
        return self._session.execute(
            select(ImageUpload).where(
                ImageUpload.id == upload_id,
                ImageUpload.owner_user_id == owner_user_id,
                ImageUpload.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def delete_owned(self, upload_id: UUID, *, owner_user_id: UUID) -> bool:
        """Remove the object and mark the row deleted. The row itself survives.

        Keeping the row means a classification that referenced this image still
        explains what it classified, while the bytes are gone.
        """
        upload = self.get_owned(upload_id, owner_user_id=owner_user_id)
        if upload is None:
            return False
        self._store.delete(upload.storage_path)
        upload.deleted_at = func.now()
        self._session.commit()
        logger.info("image upload deleted", extra={"upload_id": str(upload_id)})
        return True

    def _build_path(self, owner_user_id: UUID, mime_type: str) -> str:
        """A server-generated key. Nothing the caller sent contributes to it."""
        extension = _EXTENSIONS.get(mime_type, "bin")
        return f"{UPLOAD_PREFIX}/{owner_user_id}/{uuid4()}.{extension}"

    def _remove_quietly(self, storage_path: str) -> None:
        """Best-effort cleanup on a failed write; never masks the real error."""
        try:
            self._store.delete(storage_path)
        except (AdapterError, OSError):
            logger.warning("orphaned object could not be removed after a failed write")


def _to_stored(upload: ImageUpload, *, is_new: bool) -> StoredUpload:
    return StoredUpload(
        upload_id=upload.id,
        sha256=upload.sha256,
        mime_type=upload.mime_type,
        byte_size=upload.byte_size,
        pixel_width=upload.pixel_width,
        pixel_height=upload.pixel_height,
        is_new=is_new,
    )
