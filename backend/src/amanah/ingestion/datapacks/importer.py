"""Manifest-validated open-datapack import (B-S9A).

This is an importer, not a crawler. It reads a file that is already on disk,
under a manifest a person reviewed, and it has no code path that downloads
anything: `spec.md` section 10.4 rules out an ungoverned acquisition path, and
the way to guarantee that is not to write one.

The order of operations is the safety property. Validation — manifest, approval,
licence, file hash, encoding, required columns — happens **before any content
write**, so a package that turns out to be wrong leaves nothing behind to clean
up. Only then does the file get streamed, in batches, under the configured row
limit.

Every imported row is source `open_datapack` and public platform `N/A`, and its
real lineage — provider, dataset, version, licence, file hash, import run, row
identity — lives in its own columns. `N/A` is a display value; it never means the
provenance was lost.

Original dataset labels arrive as `dataset_annotations` and stop there. A dataset
saying a row is hateful is evidence about that dataset's labelling, and quietly
promoting it into an Amanah prediction would put a judgement into the product
that nothing in the product made.
"""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.canonical.encryption import ContentCipher
from amanah.canonical.hashing import datapack_source_item_id
from amanah.canonical.store import ContentStore
from amanah.canonical.text import normalize_text
from amanah.db.models.datasets import DatasetImportRun, DatasetPackage
from amanah.db.models.sources import OPEN_DATAPACK_SOURCE_KEY, Source
from amanah.domain.enums import ContentKind, JobState
from amanah.ingestion.contract import (
    CanonicalContentItem,
    ContentContext,
    DatasetRowProvenance,
)
from amanah.ingestion.datapacks.manifest import DatapackManifest, ManifestError, verify_file

logger = logging.getLogger(__name__)

#: Rows committed per transaction. Small enough that a failure loses little,
#: large enough that a hundred-thousand-row dataset does not take a hundred
#: thousand round trips.
BATCH_SIZE = 500

#: Ceiling on rows from one import, whatever the manifest asks for.
MAXIMUM_ROWS = 200_000

#: Cap on one row's text. A dataset cell that is megabytes long is a malformed
#: row, not a document worth keeping.
MAXIMUM_ROW_CHARACTERS = 20_000


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """What one import did, in counts an operator can act on."""

    dataset_package_id: UUID
    dataset_import_run_id: UUID
    imported: int
    skipped: int
    errors: int
    row_error_codes: tuple[str, ...]


class DatapackImporter:
    """Validates a reviewed package, then streams it into canonical storage."""

    def __init__(self, session: Session, *, cipher: ContentCipher | None = None) -> None:
        self._session = session
        self._store = ContentStore(session, cipher=cipher)

    def import_package(self, manifest: DatapackManifest, path: Path) -> ImportSummary:
        """Import one reviewed datapack file.

        Raises `ManifestError` before writing anything when the package is not
        importable. Row-level problems, by contrast, are counted and skipped: one
        malformed line must not discard the rest of a dataset.
        """
        manifest.require_approved()
        verify_file(manifest, path)
        header = _read_header(manifest, path)
        _require_columns(manifest, header)

        package_id = self._upsert_package(manifest)
        run_id = self._start_import_run(package_id)
        source_id = self._open_datapack_source_id()

        imported = skipped = errors = 0
        error_codes: list[str] = []
        try:
            for batch in _batched(_read_rows(manifest, path), BATCH_SIZE):
                for row_number, row in batch:
                    outcome = self._import_row(
                        manifest,
                        row,
                        row_number=row_number,
                        source_id=source_id,
                        package_id=package_id,
                        run_id=run_id,
                    )
                    if outcome is None:
                        errors += 1
                        error_codes.append("row_invalid")
                    elif outcome:
                        imported += 1
                    else:
                        skipped += 1
                self._session.commit()
        except Exception:
            self._session.rollback()
            self._finish_import_run(
                run_id,
                status=JobState.failed,
                imported=imported,
                skipped=skipped,
                errors=errors,
                safe_error_code="datapack_import_failed",
            )
            raise

        self._finish_import_run(
            run_id,
            status=JobState.succeeded,
            imported=imported,
            skipped=skipped,
            errors=errors,
            safe_error_code=None,
        )
        logger.info(
            "datapack imported",
            extra={
                "dataset_package_id": str(package_id),
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
            },
        )
        return ImportSummary(
            dataset_package_id=package_id,
            dataset_import_run_id=run_id,
            imported=imported,
            skipped=skipped,
            errors=errors,
            row_error_codes=tuple(dict.fromkeys(error_codes)),
        )

    # -- one row ----------------------------------------------------------

    def _import_row(
        self,
        manifest: DatapackManifest,
        row: Mapping[str, Any],
        *,
        row_number: int,
        source_id: UUID,
        package_id: UUID,
        run_id: UUID,
    ) -> bool | None:
        """Import one row. `True` stored, `False` skipped, `None` invalid.

        Nothing about the row's text reaches a log line, whatever goes wrong: a
        malformed row from a hate-speech dataset is still a row from a
        hate-speech dataset.
        """
        mapping = manifest.schema_mapping
        text = _cell(row, mapping.text_column)
        if not text:
            return None
        if len(text) > MAXIMUM_ROW_CHARACTERS:
            return None

        row_id = _row_identity(manifest, row, row_number)
        source_item_id = datapack_source_item_id(
            provider=manifest.provider,
            name=manifest.name,
            version=manifest.version,
            row_id=row_id,
        )
        item = CanonicalContentItem(
            source_key=OPEN_DATAPACK_SOURCE_KEY,
            source_item_id=source_item_id,
            content_kind=ContentKind.dataset_record,
            observed_at=manifest.retrieved_at,
            is_fixture=False,
            canonical_url=_cell(row, mapping.url_column),
            title=_cell(row, mapping.title_column),
            # A dataset row's text is the record. There is no separate licensed
            # excerpt, so the permitted excerpt is the text itself.
            permitted_excerpt=text,
            original_text=text,
            published_at=_parse_time(_cell(row, mapping.published_at_column)),
            language=_cell(row, mapping.language_column),
            country_code=_country(_cell(row, mapping.country_column)),
            context=ContentContext(title=_cell(row, mapping.title_column)),
            dataset=DatasetRowProvenance(
                dataset_package_id=package_id,
                dataset_import_run_id=run_id,
                dataset_row_id=row_id,
            ),
            dataset_annotations={
                column: _cell(row, column)
                for column in mapping.annotation_columns
                if _cell(row, column) is not None
            },
        )
        stored = self._store.upsert(item, source_id=source_id, collection_run_id=None)
        return stored.is_new

    # -- provenance rows --------------------------------------------------

    def _upsert_package(self, manifest: DatapackManifest) -> UUID:
        values = {
            "provider": manifest.provider,
            "name": manifest.name,
            "version": manifest.version,
            "landing_page_url": manifest.landing_page_url,
            "license_id": manifest.license_id,
            "license_url": manifest.license_url,
            "permitted_uses": manifest.permitted_uses,
            "approval_status": manifest.approval_status,
            "approved_by": manifest.approved_by,
            "retrieved_at": manifest.retrieved_at,
            "file_sha256": manifest.file_sha256,
            "schema_mapping_version": manifest.schema_mapping_version,
        }
        package_id = self._session.execute(
            insert(DatasetPackage)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[
                    DatasetPackage.provider,
                    DatasetPackage.name,
                    DatasetPackage.version,
                ],
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"provider", "name", "version"}
                },
            )
            .returning(DatasetPackage.id)
        ).scalar_one()
        self._session.commit()
        return package_id

    def _start_import_run(self, package_id: UUID) -> UUID:
        run_id = self._session.execute(
            insert(DatasetImportRun)
            .values(dataset_package_id=package_id, status=JobState.running)
            .returning(DatasetImportRun.id)
        ).scalar_one()
        self._session.commit()
        return run_id

    def _finish_import_run(
        self,
        run_id: UUID,
        *,
        status: JobState,
        imported: int,
        skipped: int,
        errors: int,
        safe_error_code: str | None,
    ) -> None:
        run = self._session.get_one(DatasetImportRun, run_id)
        run.status = status
        run.imported_count = imported
        run.skipped_count = skipped
        run.error_count = errors
        run.row_count = imported + skipped + errors
        run.safe_error_code = safe_error_code
        run.completed_at = datetime.now(UTC)
        self._session.commit()

    def _open_datapack_source_id(self) -> UUID:
        source_id = self._session.execute(
            select(Source.id).where(Source.source_key == OPEN_DATAPACK_SOURCE_KEY)
        ).scalar_one_or_none()
        if source_id is None:
            raise ManifestError(
                "open_datapack_source_missing",
                "The controlled open-datapack source row is not configured.",
            )
        return source_id


# -- file reading ---------------------------------------------------------


def _read_header(manifest: DatapackManifest, path: Path) -> tuple[str, ...]:
    """Read the column names, refusing a file that is not valid UTF-8."""
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            if manifest.file_format == "csv":
                reader = csv.reader(handle)
                return tuple(next(reader, []))
            first = handle.readline()
    except UnicodeDecodeError as exc:
        raise ManifestError(
            "datapack_encoding_invalid", "The datapack file is not valid UTF-8."
        ) from exc
    except OSError as exc:
        raise ManifestError(
            "datapack_file_unreadable", "The datapack file could not be read."
        ) from exc

    if not first.strip():
        return ()
    try:
        record = json.loads(first)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            "datapack_row_malformed", "The first JSONL record is not valid JSON."
        ) from exc
    return tuple(record) if isinstance(record, dict) else ()


def _require_columns(manifest: DatapackManifest, header: tuple[str, ...]) -> None:
    missing = [
        column for column in manifest.schema_mapping.required_columns if column not in header
    ]
    if missing:
        raise ManifestError(
            "datapack_columns_missing",
            "The datapack file does not contain every column its schema mapping requires.",
        )


def _read_rows(manifest: DatapackManifest, path: Path) -> Iterator[tuple[int, Mapping[str, Any]]]:
    """Stream rows, bounded by the manifest's limit and the hard ceiling."""
    limit = min(manifest.row_limit or MAXIMUM_ROWS, MAXIMUM_ROWS)
    with path.open("r", encoding="utf-8", newline="") as handle:
        if manifest.file_format == "csv":
            for number, row in enumerate(csv.DictReader(handle), start=1):
                if number > limit:
                    return
                yield number, row
            return
        for number, line in enumerate(handle, start=1):
            if number > limit:
                return
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # A malformed line is counted by the caller as a row error. The
                # line itself is never logged.
                yield number, {}
                continue
            yield number, record if isinstance(record, dict) else {}


def _batched(
    rows: Iterator[tuple[int, Mapping[str, Any]]], size: int
) -> Iterator[list[tuple[int, Mapping[str, Any]]]]:
    batch: list[tuple[int, Mapping[str, Any]]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _row_identity(manifest: DatapackManifest, row: Mapping[str, Any], row_number: int) -> str:
    """The dataset's own row identifier, or a deterministic stand-in.

    The stand-in hashes the row's *text* rather than its position, so re-importing
    a file whose lines were reordered still resolves to the same rows.
    """
    column = manifest.schema_mapping.row_id_column
    if column:
        value = _cell(row, column)
        if value:
            return value
    text = _cell(row, manifest.schema_mapping.text_column) or str(row_number)
    return datapack_source_item_id(
        provider=manifest.provider, name=manifest.name, version=manifest.version, row_id=text
    )


def _cell(row: Mapping[str, Any], column: str | None) -> str | None:
    if column is None:
        return None
    value = row.get(column)
    if value is None:
        return None
    return normalize_text(str(value)) or None


def _country(value: str | None) -> str | None:
    """Accept a two-letter code and nothing else."""
    if value is None:
        return None
    code = value.strip().upper()
    return code if len(code) == 2 and code.isalpha() else None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
