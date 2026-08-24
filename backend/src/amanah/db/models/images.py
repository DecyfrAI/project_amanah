"""The image-evidence catalog and its classifications (B-S26.2, ADR 0007).

ADR 0007 settles the storage question and this schema is that decision written
down: **object storage holds the bytes, Postgres holds the metadata**. There is
no bytes column, no base64 column, and no place for one. A row records where the
file is, what its digest is, what the source dataset said about it, and what
Amanah's own classifier concluded — four different claims that stay in four
different columns.

The separation between `dataset_annotation` and a prediction is the same rule the
open-datapack importer already follows: a label that shipped with someone else's
dataset is provenance about that dataset, never a finding this product made. They
live in different tables here for exactly that reason.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.db.models.analysis import MAXIMUM_SEVERITY, MINIMUM_SEVERITY
from amanah.db.models.datasets import DatasetPackage
from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    InferenceStatus,
    PublicationStatus,
    Relevance,
    Stance,
)

#: Media types the catalog accepts. An allowlist rather than a pattern: a
#: research corpus of static memes has no reason to hold a format nobody reviewed.
ALLOWED_IMAGE_MIME_TYPES = ("image/png", "image/jpeg", "image/webp")

#: The same allowlist as a SQL literal list, so the constraint and the Python
#: tuple cannot drift. Built from the constant above and never from input.
_MIME_TYPE_SQL_LIST = ", ".join(f"'{mime_type}'" for mime_type in ALLOWED_IMAGE_MIME_TYPES)


class ImageExample(Base):
    """One catalogued image, by reference.

    `storage_path` is a private object-storage key, not a URL. The API mints a
    short-lived signed URL from it per request; storing a durable link would make
    the corpus reachable by anyone who ever saw one response.
    """

    __tablename__ = "image_examples"
    __table_args__ = (
        # One row per file per package. Re-importing a manifest converges rather
        # than duplicating the catalog.
        UniqueConstraint(
            "dataset_package_id",
            "dataset_row_id",
            name="image_examples_dataset_package_id_dataset_row_id_unique",
        ),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint("byte_size > 0", name="byte_size_positive"),
        CheckConstraint(
            f"mime_type IN ({_MIME_TYPE_SQL_LIST})",
            name="mime_type_allowed",
        ),
        CheckConstraint(
            f"annotation_severity IS NULL OR (annotation_severity >= {MINIMUM_SEVERITY} "
            f"AND annotation_severity <= {MAXIMUM_SEVERITY})",
            name="annotation_severity_range",
        ),
        # Alt text is what a screen-reader user gets instead of the image. A row
        # without it is inaccessible, so it is required rather than encouraged.
        CheckConstraint("length(btrim(alt_text)) > 0", name="alt_text_present"),
        Index("image_examples_dataset_package_id_idx", "dataset_package_id"),
        Index(
            "image_examples_publication_status_idx",
            "publication_status",
            postgresql_where=text("publication_status = 'published'"),
        ),
    )

    id: Mapped[UuidPrimaryKey]
    dataset_package_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("dataset_packages.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_row_id: Mapped[str] = mapped_column(String(400), nullable=False)

    storage_path: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Private object-storage key. Never returned to a client."
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    title: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Describes the form of the image. Never reproduces a slur."
    )
    alt_text: Mapped[str] = mapped_column(Text, nullable=False)
    form_note: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="",
        doc="What visual device the image uses, for a reader who will not reveal it.",
    )

    # Labels the source dataset shipped. Provenance about that dataset, never an
    # Amanah finding: the columns are named `annotation_*` so a query cannot
    # mistake one for the other.
    annotation_hate_types: Mapped[list[HateType]] = mapped_column(
        ARRAY(enum_column(HateType)), nullable=False, server_default=text("'{}'")
    )
    annotation_severity: Mapped[int | None] = mapped_column(SmallInteger)
    annotation_note: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    publication_status: Mapped[PublicationStatus] = mapped_column(
        enum_column(PublicationStatus), nullable=False, server_default="draft"
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    dataset_package: Mapped[DatasetPackage] = relationship()


class ImageClassification(Base):
    """One staged classification of one catalogued image.

    Mirrors `predictions` in shape and in rule: keyed by the version triple that
    produced it, so a retry converges and a new model version adds history. It is
    a separate table rather than a nullable column on `predictions` because a
    prediction points at a `content_item` and an image example is not one.
    """

    __tablename__ = "image_classifications"
    __table_args__ = (
        UniqueConstraint(
            "image_example_id",
            "model_name",
            "model_version",
            "prompt_version",
            name="image_classifications_image_model_prompt_version_unique",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        CheckConstraint(
            f"severity >= {MINIMUM_SEVERITY} AND severity <= {MAXIMUM_SEVERITY}",
            name="severity_range",
        ),
        CheckConstraint(
            "inference_status = 'succeeded' OR stance <> 'likely_anti_muslim'",
            # Shortened from the wording `predictions` uses: the convention
            # prefixes the table name and appends `_check`, and the longer stem
            # would exceed Postgres's 63-character identifier limit.
            name="unsuccessful_makes_no_claim",
        ),
        Index(
            "image_classifications_image_example_id_created_at_idx",
            "image_example_id",
            text("created_at DESC"),
        ),
    )

    id: Mapped[UuidPrimaryKey]
    image_example_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("image_examples.id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[UuidColumn | None] = mapped_column(
        doc="The signed-in user who asked for this classification."
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(50), nullable=False)

    relevance: Mapped[Relevance] = mapped_column(enum_column(Relevance), nullable=False)
    stance: Mapped[Stance] = mapped_column(enum_column(Stance), nullable=False)
    hate_types: Mapped[list[HateType]] = mapped_column(
        ARRAY(enum_column(HateType)), nullable=False, server_default=text("'{}'")
    )
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    narrative_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_tier: Mapped[ConfidenceTier] = mapped_column(
        enum_column(ConfidenceTier), nullable=False
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    requires_review: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    inference_status: Mapped[InferenceStatus] = mapped_column(
        enum_column(InferenceStatus), nullable=False, server_default="succeeded"
    )
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Safe call metadata. Never image bytes and never a provider body.",
    )
    inferred_at: Mapped[Timestamp | None]
    created_at: Mapped[CreatedAt]

    image_example: Mapped[ImageExample] = relationship()
