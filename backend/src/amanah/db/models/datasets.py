"""Reviewed open-datapack provenance.

A datapack row displays `N/A` as its public source and platform. Everything that
says where it actually came from lives here, so the display value never erases
lineage. Nothing may be imported without a reviewed manifest, a verified file
hash, and a recorded licence.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.domain.enums import ApprovalStatus, JobState


class DatasetPackage(Base):
    """One reviewed version of one open dataset."""

    __tablename__ = "dataset_packages"
    __table_args__ = (
        UniqueConstraint(
            "provider", "name", "version", name="dataset_packages_provider_name_version_unique"
        ),
        CheckConstraint("file_sha256 ~ '^[0-9a-f]{64}$'", name="file_sha256_format"),
        CheckConstraint(
            "landing_page_url LIKE 'https://%'",
            name="landing_page_url_https",
        ),
        # Approval and an approver travel together: an approved package with no
        # named approver would be an unaccountable import.
        CheckConstraint(
            "approval_status <> 'approved' OR approved_by IS NOT NULL",
            name="approved_by_required",
        ),
        Index("dataset_packages_approval_status_idx", "approval_status"),
    )

    id: Mapped[UuidPrimaryKey]
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(200), nullable=False)
    landing_page_url: Mapped[str] = mapped_column(Text, nullable=False)
    license_id: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="SPDX identifier or the provider's licence name."
    )
    license_url: Mapped[str | None] = mapped_column(Text)
    permitted_uses: Mapped[str] = mapped_column(
        Text, nullable=False, doc="What the reviewed licence allows, in plain language."
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_column(ApprovalStatus), nullable=False, server_default="pending"
    )
    approved_by: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[Timestamp] = mapped_column(nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_mapping_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    import_runs: Mapped[list[DatasetImportRun]] = relationship(back_populates="dataset_package")


class DatasetImportRun(Base):
    """One execution of the importer against one reviewed package."""

    __tablename__ = "dataset_import_runs"
    __table_args__ = (
        CheckConstraint(
            "imported_count >= 0 AND skipped_count >= 0 AND error_count >= 0",
            name="counts_non_negative",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completion_after_start",
        ),
        Index("dataset_import_runs_dataset_package_id_idx", "dataset_package_id"),
        Index("dataset_import_runs_status_started_at_idx", "status", "started_at"),
    )

    id: Mapped[UuidPrimaryKey]
    dataset_package_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("dataset_packages.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[JobState] = mapped_column(
        enum_column(JobState), nullable=False, server_default="queued"
    )
    row_count: Mapped[int | None] = mapped_column(Integer)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    safe_error_code: Mapped[str | None] = mapped_column(
        String(100), doc="Stable code only; never a provider or parser message."
    )
    started_at: Mapped[CreatedAt]
    completed_at: Mapped[Timestamp | None]

    dataset_package: Mapped[DatasetPackage] = relationship(back_populates="import_runs")
