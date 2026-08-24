"""Authenticated user image uploads and their classifications (B-S28).

The existing schema represents a *reviewed catalogue*: every image belongs to a
dataset package, and every row is administrator-curated. It has nowhere to put a
file one signed-in person uploaded from their own device, which is a different
thing with a different owner, a different lifetime, and a different reader.

So this adds `image_uploads` beside `image_examples` rather than widening it.
The two never merge: an owner column on the corpus, or a dataset column on a
personal file, would let one row type be read through the other's policies.

`image_classifications` gains `image_upload_id` and its `image_example_id`
becomes nullable, under a check requiring **exactly one** subject. A row with
both would make "whose image is this?" unanswerable, and that question decides
who may read the classification.

Authorization, stated as policy rather than as convention:

* Anonymous reaches nothing. Base grants are revoked and RLS is forced, so even
  a direct PostgREST query sees no row.
* An upload is readable by its owner alone. Not by another user, and not by a
  reviewer: a reviewer's remit is classified public material, not a colleague's
  private file.
* An administrator may read and delete, because retention has to be operable.
* The projection carries no `storage_path` and no bucket, exactly as the
  catalogue's does. A reader receives a short-lived signed URL minted
  server-side, never a durable location.

Revision ID: 0008_user_image_uploads
Revises: 0007_merge_milestone_heads
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_user_image_uploads"
down_revision: str | None = "0007_merge_milestone_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Mirrors `ALLOWED_IMAGE_MIME_TYPES` in `amanah.db.models.images`. Written as a
#: literal list rather than interpolated from input.
_ALLOWED_MIME_TYPES = "'image/png', 'image/jpeg', 'image/webp'"

_UPLOAD_VIEW = """
-- One person's own uploads. Carries no `storage_path` and no bucket: a reader
-- receives a short-lived signed URL minted server-side, so a saved response
-- cannot become a durable link to private storage (ADR 0007, B-S28).
--
-- Rows whose object has been deleted under retention are excluded. The row
-- survives so a classification still explains what it classified, but there is
-- nothing left to serve.
CREATE VIEW public.authenticated_image_uploads WITH (security_barrier = true) AS
SELECT
  upload.id,
  upload.owner_user_id,
  upload.mime_type,
  upload.byte_size,
  upload.sha256,
  upload.pixel_width,
  upload.pixel_height,
  upload.created_at,
  upload.retention_expires_at,
  latest.score,
  latest.narrative_tags,
  latest.rationale,
  latest.relevance::text       AS relevance,
  latest.stance::text          AS stance,
  latest.confidence_tier::text AS confidence_tier,
  latest.severity              AS predicted_severity,
  latest.hate_types            AS predicted_hate_types,
  latest.requires_review,
  latest.model_name,
  latest.model_version,
  latest.taxonomy_version
FROM public.image_uploads AS upload
LEFT JOIN LATERAL (
  SELECT
    classification.score, classification.narrative_tags, classification.rationale,
    classification.relevance, classification.stance, classification.confidence_tier,
    classification.severity, classification.hate_types, classification.requires_review,
    classification.model_name, classification.model_version, classification.taxonomy_version
  FROM public.image_classifications AS classification
  WHERE classification.image_upload_id = upload.id
    AND classification.inference_status = 'succeeded'
  ORDER BY classification.created_at DESC, classification.id DESC
  LIMIT 1
) AS latest ON TRUE
WHERE upload.deleted_at IS NULL
  AND upload.owner_user_id = public.amanah_current_user_id();
"""


def _create_image_uploads() -> None:
    op.create_table(
        "image_uploads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_bucket", sa.String(length=63), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("pixel_width", sa.Integer(), nullable=False),
        sa.Column("pixel_height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="image_uploads_pkey"),
        sa.UniqueConstraint(
            "owner_user_id", "sha256", name="image_uploads_owner_user_id_sha256_unique"
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        sa.CheckConstraint("byte_size > 0", name="byte_size_positive"),
        sa.CheckConstraint(f"mime_type IN ({_ALLOWED_MIME_TYPES})", name="mime_type_allowed"),
        sa.CheckConstraint("pixel_width > 0 AND pixel_height > 0", name="dimensions_positive"),
        sa.CheckConstraint("length(btrim(storage_path)) > 0", name="storage_path_present"),
        sa.CheckConstraint(
            "retention_expires_at IS NULL OR retention_expires_at >= created_at",
            name="retention_after_creation",
        ),
        sa.CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at", name="deletion_after_creation"
        ),
        schema="public",
    )
    op.create_index(
        "image_uploads_owner_user_id_created_at_idx",
        "image_uploads",
        ["owner_user_id", sa.text("created_at DESC")],
        schema="public",
    )


def _link_classifications_to_uploads() -> None:
    """Let a classification point at an upload, and require exactly one subject."""
    op.add_column(
        "image_classifications",
        sa.Column("image_upload_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "image_classifications_image_upload_id_fkey",
        "image_classifications",
        "image_uploads",
        ["image_upload_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="CASCADE",
    )
    # Existing rows all reference a catalogue example, so relaxing this column is
    # safe: nothing becomes null that was not already set.
    op.alter_column(
        "image_classifications",
        "image_example_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
        schema="public",
    )
    op.create_check_constraint(
        "exactly_one_subject",
        "image_classifications",
        "(image_example_id IS NULL) <> (image_upload_id IS NULL)",
        schema="public",
    )
    op.create_unique_constraint(
        "image_classifications_upload_model_prompt_version_unique",
        "image_classifications",
        ["image_upload_id", "model_name", "model_version", "prompt_version"],
        schema="public",
    )
    op.create_index(
        "image_classifications_image_upload_id_created_at_idx",
        "image_classifications",
        ["image_upload_id", sa.text("created_at DESC")],
        schema="public",
    )


def _secure_image_uploads() -> None:
    """Deny by default, then name exactly who may reach an upload."""
    op.execute("ALTER TABLE public.image_uploads ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.image_uploads FORCE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON public.image_uploads FROM anon, PUBLIC, authenticated")

    # The owner, and nobody else. Deliberately not extended to reviewers: their
    # remit is classified public material, not a colleague's private file.
    op.execute(
        "CREATE POLICY image_uploads_owner_read ON public.image_uploads "
        "FOR SELECT TO authenticated "
        "USING (owner_user_id = public.amanah_current_user_id())"
    )
    # Retention has to be operable, so an administrator may read and remove.
    op.execute(
        "CREATE POLICY image_uploads_administrator_all ON public.image_uploads "
        "FOR ALL TO authenticated "
        "USING (public.amanah_is_administrator()) "
        "WITH CHECK (public.amanah_is_administrator())"
    )
    # A classification of an upload follows the upload's own visibility, so a
    # label about someone's private file is not readable by anyone else.
    op.execute(
        "CREATE POLICY image_classifications_upload_owner_read "
        "ON public.image_classifications "
        "FOR SELECT TO authenticated "
        "USING ("
        "  image_upload_id IS NOT NULL"
        "  AND EXISTS ("
        "    SELECT 1 FROM public.image_uploads AS owned"
        "    WHERE owned.id = image_classifications.image_upload_id"
        "      AND owned.owner_user_id = public.amanah_current_user_id()"
        "  )"
        ")"
    )


def upgrade() -> None:
    _create_image_uploads()
    _link_classifications_to_uploads()
    _secure_image_uploads()
    op.execute(_UPLOAD_VIEW)
    op.execute("GRANT SELECT ON public.authenticated_image_uploads TO authenticated")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.authenticated_image_uploads")
    op.execute(
        "DROP POLICY IF EXISTS image_classifications_upload_owner_read "
        "ON public.image_classifications"
    )
    op.execute("DROP POLICY IF EXISTS image_uploads_administrator_all ON public.image_uploads")
    op.execute("DROP POLICY IF EXISTS image_uploads_owner_read ON public.image_uploads")

    op.drop_index(
        "image_classifications_image_upload_id_created_at_idx",
        table_name="image_classifications",
        schema="public",
    )
    # Literal SQL rather than `op.drop_constraint`: the metadata naming
    # convention re-expands a name passed to that helper, turning an
    # already-qualified constraint name into a second, non-existent one.
    for constraint in (
        "image_classifications_upload_model_prompt_version_unique",
        "image_classifications_exactly_one_subject_check",
    ):
        op.execute(
            f"ALTER TABLE public.image_classifications DROP CONSTRAINT IF EXISTS {constraint}"
        )
    # Restoring NOT NULL requires every row to name a catalogue example. Rows
    # created for an upload cannot satisfy that, so they are removed first —
    # they are classifications of objects this downgrade also drops.
    op.execute("DELETE FROM public.image_classifications WHERE image_example_id IS NULL")
    op.alter_column(
        "image_classifications",
        "image_example_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        schema="public",
    )
    op.execute(
        "ALTER TABLE public.image_classifications "
        "DROP CONSTRAINT IF EXISTS image_classifications_image_upload_id_fkey"
    )
    op.drop_column("image_classifications", "image_upload_id", schema="public")

    op.drop_index(
        "image_uploads_owner_user_id_created_at_idx", table_name="image_uploads", schema="public"
    )
    op.drop_table("image_uploads", schema="public")
