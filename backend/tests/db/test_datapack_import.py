"""Reviewed open-datapack import (B-S9A.9).

Two things are proved here. That a package which fails review leaves **nothing**
behind — validation happens before any content write, so a wrong hash or an
unapproved licence cannot half-import a dataset. And that a row which does get
in keeps its whole lineage, even though its public source and platform read
`N/A`.

Every dataset in these tests is invented. The text is deliberately bland: what
is under test is provenance and idempotency, and reproducing real hateful
material to prove that a CSV parser works would be gratuitous.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from amanah.db.models.content import ContentItem
from amanah.db.models.datasets import DatasetImportRun, DatasetPackage
from amanah.domain.enums import ApprovalStatus, ContentKind, JobState, PublicPlatform
from amanah.ingestion.datapacks.importer import DatapackImporter
from amanah.ingestion.datapacks.manifest import DatapackManifest, ManifestError, SchemaMapping
from tests.db import factories
from tests.db.conftest import act_as, claims_for

ROWS = [
    {"row_id": "1", "text": "A neutral sentence from a research dataset.", "label": "none"},
    {"row_id": "2", "text": "Another neutral sentence.", "label": "offensive"},
    {"row_id": "3", "text": "A third neutral sentence.", "label": "none"},
]


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as active:
        yield active


@pytest.fixture
def datapack_source(engine: Engine) -> None:
    """The single controlled `N/A` source every imported row points at."""
    with engine.begin() as connection:
        factories.insert_open_datapack_source(connection)


def _write_csv(directory: Path, rows: list[dict[str, str]] | None = None) -> Path:
    path = directory / "dataset.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_id", "text", "label"])
        writer.writeheader()
        writer.writerows(rows if rows is not None else ROWS)
    return path


def _write_jsonl(directory: Path, rows: list[dict[str, Any]] | None = None) -> Path:
    path = directory / "dataset.jsonl"
    lines = [json.dumps(row) for row in (rows if rows is not None else ROWS)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(path: Path, **overrides: Any) -> DatapackManifest:
    values: dict[str, Any] = {
        "provider": "synthetic-provider",
        "name": "synthetic-hate-speech-corpus",
        "version": "1.0.0",
        "landing_page_url": "https://example.test/datasets/synthetic",
        "license_id": "CC-BY-4.0",
        "license_url": "https://example.test/licenses/cc-by-4.0",
        "permitted_uses": "Research use with attribution.",
        "retrieved_at": datetime(2026, 8, 1, tzinfo=UTC),
        "file_sha256": _digest(path),
        "file_format": path.suffix.lstrip("."),
        "schema_mapping_version": "1",
        "schema_mapping": SchemaMapping(
            text_column="text", row_id_column="row_id", annotation_columns=("label",)
        ),
        "is_fixture": False,
        "approval_status": ApprovalStatus.approved,
        "approved_by": "reviewer",
    }
    values.update(overrides)
    return DatapackManifest.model_validate(values)


def _item_count(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(ContentItem)).scalar_one())


# -- refusal before any write ---------------------------------------------


def test_an_unapproved_package_writes_nothing(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_csv(tmp_path)
    manifest = _manifest(path, approval_status=ApprovalStatus.pending)

    with pytest.raises(ManifestError) as raised:
        DatapackImporter(session).import_package(manifest, path)

    assert raised.value.safe_code == "datapack_not_approved"
    assert _item_count(session) == 0
    assert session.execute(select(func.count()).select_from(DatasetPackage)).scalar_one() == 0


def test_an_approved_package_with_no_approver_is_refused(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """An approved package nobody is named against is an unaccountable import."""
    del datapack_source
    path = _write_csv(tmp_path)
    manifest = _manifest(path, approved_by=None)

    with pytest.raises(ManifestError) as raised:
        DatapackImporter(session).import_package(manifest, path)

    assert raised.value.safe_code == "datapack_approver_missing"


def test_a_hash_mismatch_writes_nothing(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """The file on disk must be the file that was reviewed."""
    del datapack_source
    path = _write_csv(tmp_path)
    manifest = _manifest(path, file_sha256="0" * 64)

    with pytest.raises(ManifestError) as raised:
        DatapackImporter(session).import_package(manifest, path)

    assert raised.value.safe_code == "datapack_hash_mismatch"
    assert _item_count(session) == 0


def test_a_file_that_is_not_utf8_is_refused(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    path = tmp_path / "dataset.csv"
    path.write_bytes(b"row_id,text,label\n1,\xff\xfe not utf-8,none\n")
    del datapack_source

    with pytest.raises(ManifestError) as raised:
        DatapackImporter(session).import_package(_manifest(path), path)

    assert raised.value.safe_code == "datapack_encoding_invalid"
    assert _item_count(session) == 0


def test_a_missing_required_column_is_refused(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = tmp_path / "dataset.csv"
    path.write_text("identifier,body\n1,text\n", encoding="utf-8")

    with pytest.raises(ManifestError) as raised:
        DatapackImporter(session).import_package(_manifest(path), path)

    assert raised.value.safe_code == "datapack_columns_missing"
    assert _item_count(session) == 0


def test_a_missing_file_is_refused(session: Session, datapack_source: None, tmp_path: Path) -> None:
    del datapack_source
    path = _write_csv(tmp_path)
    manifest = _manifest(path)

    with pytest.raises(ManifestError):
        DatapackImporter(session).import_package(manifest, tmp_path / "absent.csv")


def test_an_unsupported_format_is_refused_by_the_manifest_itself(tmp_path: Path) -> None:
    """Parquet may follow, but adding it is a code change and a review."""
    path = _write_csv(tmp_path)

    with pytest.raises(ValueError, match="file_format"):
        _manifest(path, file_format="parquet")


# -- successful import ----------------------------------------------------


def test_a_reviewed_csv_imports_and_records_its_counts(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_csv(tmp_path)

    summary = DatapackImporter(session).import_package(_manifest(path), path)

    assert summary.imported == 3
    assert summary.errors == 0
    assert _item_count(session) == 3

    run = session.get_one(DatasetImportRun, summary.dataset_import_run_id)
    assert run.status is JobState.succeeded
    assert run.imported_count == 3
    assert run.completed_at is not None


def test_a_reviewed_jsonl_imports_the_same_way(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_jsonl(tmp_path)

    summary = DatapackImporter(session).import_package(_manifest(path), path)

    assert summary.imported == 3


def test_every_row_publishes_not_applicable_while_keeping_its_lineage(
    session: Session, datapack_source: None, tmp_path: Path, engine: Engine
) -> None:
    """B-S9A.4 and B-S9A.5. `N/A` is a display value, never lost provenance."""
    del datapack_source
    path = _write_csv(tmp_path)

    summary = DatapackImporter(session).import_package(_manifest(path), path)

    # Read the way a request does — as `authenticated`, with a verified caller
    # published — so the projection's own predicate is exercised rather than
    # bypassed by the importer's connection.
    with engine.connect() as connection:
        transaction = connection.begin()
        act_as(connection, "authenticated", claims_for(uuid4()))
        rows = connection.execute(text("SELECT * FROM public.authenticated_items")).mappings().all()
        transaction.rollback()

    assert len(rows) == 3
    assert all(row["platform"] == PublicPlatform.not_applicable.value for row in rows)
    assert all(row["source_name"] == "N/A" for row in rows)
    assert all(row["dataset_provider"] == "synthetic-provider" for row in rows)

    items = list(session.execute(select(ContentItem)).scalars())
    assert all(item.content_kind is ContentKind.dataset_record for item in items)
    assert all(item.dataset_package_id == summary.dataset_package_id for item in items)
    assert all(item.dataset_import_run_id == summary.dataset_import_run_id for item in items)
    assert {item.dataset_row_id for item in items} == {"1", "2", "3"}


def test_dataset_labels_are_annotations_and_never_predictions(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """B-S9A.6. A dataset's own judgement is evidence about that dataset."""
    del datapack_source
    path = _write_csv(tmp_path)

    DatapackImporter(session).import_package(_manifest(path), path)

    items = {item.dataset_row_id: item for item in session.execute(select(ContentItem)).scalars()}
    assert items["2"].dataset_annotations == {"label": "offensive"}
    # Nothing became an Amanah prediction.
    predictions = session.execute(text("SELECT count(*) FROM public.predictions")).scalar_one()
    assert predictions == 0
    assert all(item.effective_review_state.value == "model_only" for item in items.values())


def test_a_synthetic_datapack_remains_fixture_data(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """Manifest approval must never make synthetic rows look live."""
    del datapack_source
    path = _write_csv(tmp_path)

    DatapackImporter(session).import_package(_manifest(path, is_fixture=True), path)

    items = list(session.execute(select(ContentItem)).scalars())
    assert items
    assert all(item.is_fixture for item in items)


def test_a_source_item_id_is_deterministic_and_namespaced(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_csv(tmp_path)

    DatapackImporter(session).import_package(_manifest(path), path)

    identifiers = [item.source_item_id for item in session.execute(select(ContentItem)).scalars()]
    assert all(identifier.startswith("datapack:") for identifier in identifiers)
    assert len(set(identifiers)) == 3


# -- idempotency and collisions -------------------------------------------


def test_re_importing_the_same_package_adds_nothing(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """B-S9A.7. A retried import converges rather than doubling the dataset."""
    del datapack_source
    path = _write_csv(tmp_path)
    manifest = _manifest(path)

    DatapackImporter(session).import_package(manifest, path)
    second = DatapackImporter(session).import_package(manifest, path)

    assert _item_count(session) == 3
    assert second.imported == 0
    assert second.skipped == 3


def test_the_same_row_id_in_two_packages_produces_two_items(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """Row `1` of two different datasets is two records, not one."""
    del datapack_source
    first_path = _write_csv(tmp_path)
    second_directory = tmp_path / "other"
    second_directory.mkdir()
    second_path = _write_csv(second_directory)

    DatapackImporter(session).import_package(_manifest(first_path), first_path)
    DatapackImporter(session).import_package(
        _manifest(second_path, name="a-different-corpus"), second_path
    )

    assert _item_count(session) == 6


def test_two_versions_of_one_dataset_do_not_collide(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_csv(tmp_path)

    DatapackImporter(session).import_package(_manifest(path, version="1.0.0"), path)
    DatapackImporter(session).import_package(_manifest(path, version="2.0.0"), path)

    assert _item_count(session) == 6


# -- row-level problems ---------------------------------------------------


def test_a_malformed_row_is_counted_without_discarding_the_dataset(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """One bad line must not throw away the rest of a hundred-thousand-row file."""
    del datapack_source
    path = tmp_path / "dataset.jsonl"
    path.write_text(
        json.dumps(ROWS[0]) + "\nnot json at all\n" + json.dumps(ROWS[2]) + "\n",
        encoding="utf-8",
    )

    summary = DatapackImporter(session).import_package(_manifest(path), path)

    assert summary.imported == 2
    assert summary.errors == 1
    assert "row_invalid" in summary.row_error_codes


def test_a_row_with_no_text_is_an_error_rather_than_an_empty_item(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_csv(tmp_path, [{"row_id": "1", "text": "", "label": "none"}, ROWS[1]])

    summary = DatapackImporter(session).import_package(_manifest(path), path)

    assert summary.imported == 1
    assert summary.errors == 1


def test_the_row_limit_is_respected(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    del datapack_source
    path = _write_csv(tmp_path)

    summary = DatapackImporter(session).import_package(_manifest(path, row_limit=2), path)

    assert summary.imported == 2
    assert _item_count(session) == 2


def test_a_row_without_an_identifier_column_still_gets_stable_identity(
    session: Session, datapack_source: None, tmp_path: Path
) -> None:
    """A deterministic hash of the row's text, so re-import is still idempotent."""
    del datapack_source
    path = tmp_path / "dataset.csv"
    path.write_text("text,label\nA neutral sentence.,none\n", encoding="utf-8")
    manifest = _manifest(
        path,
        schema_mapping=SchemaMapping(text_column="text", annotation_columns=("label",)),
    )

    DatapackImporter(session).import_package(manifest, path)
    first = {item.source_item_id for item in session.execute(select(ContentItem)).scalars()}
    DatapackImporter(session).import_package(manifest, path)
    second = {item.source_item_id for item in session.execute(select(ContentItem)).scalars()}

    assert first == second
    assert _item_count(session) == 1
