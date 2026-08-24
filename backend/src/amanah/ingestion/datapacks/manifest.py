"""The reviewed datapack manifest (B-S9A.1, B-S9A.3).

A manifest is what turns "a CSV somebody downloaded" into an artifact this
product may import. It names the provider, the dataset, the exact version, where
it came from, what licence governs it, what that licence permits, when it was
retrieved, the SHA-256 of the file, how its columns map onto canonical fields,
and who approved all of that.

Every one of those is required, and the import refuses before writing anything if
any is missing or does not match the file on disk. `AGENTS.md` is unambiguous:
never import or redistribute an open datapack without a reviewed manifest, a
verified file hash, an explicit licence record, and stable row provenance. The
validation here is that sentence made executable.

Note what the schema mapping does *not* have: a slot for a label column that
becomes an Amanah prediction. Original dataset labels are imported as dataset
annotations and stay there (B-S9A.6). A dataset's own judgement about a row is
evidence about that dataset, not a finding by this product.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from amanah.domain.enums import ApprovalStatus

#: Formats P0 accepts. Parquet may follow; adding it is a code change and a
#: review, not a manifest field somebody can set.
SUPPORTED_FORMATS = frozenset({"csv", "jsonl"})

#: Read granularity when hashing. Datapacks are large, and hashing one by loading
#: it into memory would fail on exactly the files worth importing.
_HASH_CHUNK_BYTES = 1024 * 1024


class ManifestError(ValueError):
    """The manifest is invalid, or does not describe the file it points at."""

    def __init__(self, safe_code: str, message: str) -> None:
        super().__init__(message)
        self.safe_code = safe_code


class SchemaMapping(BaseModel):
    """Which columns of the dataset become which canonical fields.

    `row_id_column` is the one that carries stable row identity. When a dataset
    has none, `deterministic_row_hash` is used instead — a hash of the mapped
    values — so `(dataset_package_id, dataset_row_id)` stays a real key and an
    import can still be idempotent.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    text_column: str = Field(min_length=1)
    row_id_column: str | None = None
    title_column: str | None = None
    url_column: str | None = None
    published_at_column: str | None = None
    language_column: str | None = None
    country_column: str | None = None
    #: Columns kept as the dataset's own annotations. Never predictions.
    annotation_columns: tuple[str, ...] = ()

    @property
    def required_columns(self) -> tuple[str, ...]:
        """Columns whose absence makes the file unusable."""
        required = [self.text_column]
        if self.row_id_column:
            required.append(self.row_id_column)
        return tuple(required)


class DatapackManifest(BaseModel):
    """One reviewed dataset version, and the terms under which it may be used."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=200)
    landing_page_url: str = Field(min_length=1)
    license_id: str = Field(min_length=1, max_length=100)
    license_url: str | None = None
    permitted_uses: str = Field(min_length=1)
    retrieved_at: datetime
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_format: str
    schema_mapping_version: str = Field(min_length=1, max_length=50)
    schema_mapping: SchemaMapping
    is_fixture: bool = False
    approval_status: ApprovalStatus = ApprovalStatus.pending
    approved_by: str | None = None
    row_limit: int | None = Field(default=None, gt=0)

    @field_validator("landing_page_url")
    @classmethod
    def _check_landing_page(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("landing_page_url must be an absolute https URL")
        return value

    @field_validator("file_format")
    @classmethod
    def _check_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_FORMATS:
            raise ValueError(f"file_format must be one of {sorted(SUPPORTED_FORMATS)}")
        return normalized

    def require_approved(self) -> None:
        """Refuse an unapproved or unattributed manifest.

        Approval and an approver travel together. An approved package with nobody
        named against it is an unaccountable import, which is the situation this
        whole mechanism exists to prevent.
        """
        if self.approval_status is not ApprovalStatus.approved:
            raise ManifestError(
                "datapack_not_approved", "This datapack has not been approved for import."
            )
        if not self.approved_by:
            raise ManifestError(
                "datapack_approver_missing", "An approved datapack must name its approver."
            )


def file_sha256(path: Path) -> str:
    """Hash a datapack file in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(manifest: DatapackManifest, path: Path) -> None:
    """Refuse unless the file on disk is the one the manifest describes.

    Compared with `hmac.compare_digest` — not because a timing attack on a
    published hash is realistic, but because it is the right habit and costs
    nothing here.
    """
    import hmac

    if not path.is_file():
        raise ManifestError("datapack_file_missing", "The datapack file was not found.")
    actual = file_sha256(path)
    if not hmac.compare_digest(actual, manifest.file_sha256):
        raise ManifestError(
            "datapack_hash_mismatch",
            "The datapack file does not match the hash its manifest records.",
        )
