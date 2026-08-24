"""Reads of the image-evidence catalog (B-S26.3).

Like every repository here, these read the `authenticated_image_examples`
projection and never a base table. That is what keeps `storage_path` unreachable
from an endpoint: the column is not in the view, so no query written above this
layer can return it.

The one exception is `read_storage_target`, which reads the base table because
classifying an image requires knowing where its bytes are. It returns the path to
the *server*, never toward a response, and the route that calls it hands the path
to object storage rather than to the client.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from amanah.db.models.images import ImageExample
from amanah.db.views import authenticated_image_examples
from amanah.domain.enums import PublicationStatus

#: Upper bound on one catalog page. The corpus is a reviewed fixture pack of
#: tens of images, so this is a guard rather than pagination.
CATALOG_LIMIT = 100


class ImageCatalogRepository:
    """The authenticated image catalog and the storage targets behind it."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_examples(self, limit: int = CATALOG_LIMIT) -> tuple[Row[Any], ...]:
        """One page of published catalog entries, newest first."""
        table = authenticated_image_examples
        statement = (
            select(table).order_by(table.c.created_at.desc(), table.c.id.desc()).limit(limit)
        )
        return tuple(self._session.execute(statement).all())

    def get_example(self, example_id: UUID) -> Row[Any] | None:
        table = authenticated_image_examples
        return self._session.execute(select(table).where(table.c.id == example_id)).one_or_none()

    def read_storage_paths(self, example_ids: tuple[UUID, ...]) -> dict[UUID, str]:
        """Where these examples' bytes live, for minting signed URLs.

        Reads the base table because the projection deliberately has no
        `storage_path` column. The result is used to sign a link and is never
        placed into a response, so the durable key stays server-side.
        """
        if not example_ids:
            return {}
        statement = select(ImageExample.id, ImageExample.storage_path).where(
            ImageExample.id.in_(example_ids)
        )
        return {row.id: row.storage_path for row in self._session.execute(statement)}

    def read_storage_target(self, example_id: UUID) -> Row[Any] | None:
        """Where one published example's bytes live, for server-side reads only.

        Restricted to published rows for the same reason the projection is: a
        draft entry has not been reviewed, and classifying one would put an
        unreviewed image through the model on a caller's request.
        """
        statement = select(
            ImageExample.id,
            ImageExample.storage_path,
            ImageExample.sha256,
            ImageExample.mime_type,
        ).where(
            ImageExample.id == example_id,
            ImageExample.publication_status == PublicationStatus.published,
        )
        return self._session.execute(statement).one_or_none()
