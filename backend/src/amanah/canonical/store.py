"""Canonical persistence: normalize, deduplicate, and upsert (B-S12.6, B-S9.4).

One function does the writing, and it is idempotent by construction. Re-running a
stage against the same item updates the row it already produced rather than
creating a second one, which is what lets a retry be safe.

Deduplication is checked before the insert *and* enforced by the database after
it. The check exists so a duplicate can be reported as a duplicate — a user's
submission links to the item that already exists rather than failing — and the
constraint exists because a check alone loses a race. `spec.md` section 10.5 asks
for both canonical-URL and normalized publisher/headline dedupe on news, and the
partial unique indexes added in migration `0004` are what make that a guarantee
rather than an intention.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Table, func, literal_column, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.canonical.context import assemble_context
from amanah.canonical.encryption import ContentCipher
from amanah.canonical.hashing import content_hash, headline_key
from amanah.canonical.text import (
    NORMALIZATION_VERSION,
    normalize_language,
    normalize_text,
    truncate_excerpt,
)
from amanah.canonical.urls import canonical_url_key, safe_url
from amanah.db.models.content import ContentItem
from amanah.domain.enums import ContentKind
from amanah.ingestion.contract import CanonicalContentItem

logger = logging.getLogger(__name__)

#: Reviewed feed terms permit a short excerpt and nothing more. The value is the
#: one `docs/news-rss-sources.md` recommends.
EXCERPT_CHARACTER_LIMIT = 400


@dataclass(frozen=True, slots=True)
class StoredItem:
    """What one canonical write did.

    `is_duplicate` means the item already existed under a *different* natural
    key — the same article reached us through a second feed — and was linked
    rather than re-inserted. `is_new` distinguishes a first write from an
    idempotent re-write of the same key.
    """

    content_item_id: UUID
    is_new: bool
    is_duplicate: bool


class ContentStore:
    """Writes canonical items, and only canonical items."""

    def __init__(self, session: Session, *, cipher: ContentCipher | None = None) -> None:
        self._session = session
        self._cipher = cipher

    def find_duplicate(self, item: CanonicalContentItem) -> UUID | None:
        """Return the existing item this one duplicates, if any.

        News is checked on both documented keys. Everything else relies on
        `(source_id, source_item_id)` and on the datapack row key, which the
        upsert handles directly.
        """
        if item.content_kind is not ContentKind.news_article:
            return None

        url = safe_url(item.canonical_url)
        if url is not None:
            match = self._session.execute(
                select(ContentItem.id).where(
                    ContentItem.canonical_url_key == canonical_url_key(url)
                )
            ).scalar_one_or_none()
            if match is not None:
                return match

        key = headline_key(publisher=item.publisher_or_container, title=item.title)
        if key is None:
            return None
        return self._session.execute(
            select(ContentItem.id).where(ContentItem.headline_key == key)
        ).scalar_one_or_none()

    def upsert(
        self,
        item: CanonicalContentItem,
        *,
        source_id: UUID,
        collection_run_id: UUID | None = None,
        source_seed_entry_id: UUID | None = None,
    ) -> StoredItem:
        """Normalize, deduplicate, and write one canonical item.

        The whole normalization pass happens here rather than in each adapter, so
        an adapter cannot accidentally store text that skipped it and every row
        carries the version of the rules that produced it.
        """
        existing = self.find_duplicate(item)
        if existing is not None:
            logger.info(
                "canonical item linked to an existing row",
                extra={"content_item_id": str(existing), "source_key": item.source_key},
            )
            return StoredItem(content_item_id=existing, is_new=False, is_duplicate=True)

        values = self._to_row(
            item,
            source_id=source_id,
            collection_run_id=collection_run_id,
            source_seed_entry_id=source_seed_entry_id,
        )
        # Re-running a stage must converge on the same row. Everything derived
        # from the payload is refreshed; provenance that identifies the row is
        # not, so a second run cannot reassign an item to a different source.
        #
        # Keyed by `Column` rather than by name. `content_items` has a column
        # literally called `metadata`, and a string key of that name resolves to
        # the declarative `MetaData` object instead of the column.
        table = cast(Table, ContentItem.__table__)
        refreshable = {
            table.c[column]: values[column]
            for column in (
                "title",
                "permitted_excerpt",
                "text_ciphertext",
                "normalized_text",
                "normalization_version",
                "normalized_context",
                "canonical_url",
                "canonical_url_key",
                "headline_key",
                "publisher_or_container",
                "published_at",
                "observed_at",
                "language",
                "country_code",
                "geographic_scope",
                "source_status",
                "content_hash",
                "dataset_annotations",
                "metadata",
            )
        }
        refreshable[table.c.updated_at] = func.now()
        statement: Any = (
            insert(table)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[table.c.source_id, table.c.source_item_id],
                set_=refreshable,
            )
            # `xmax` is zero on a row this statement inserted and non-zero on one
            # it updated. Comparing timestamps would not work: both are server
            # defaults set to the same `now()` on insert.
            .returning(table.c.id, literal_column("(xmax = 0)").label("was_inserted"))
        )
        row = self._session.execute(statement).one()
        return StoredItem(
            content_item_id=row.id,
            is_new=bool(row.was_inserted),
            is_duplicate=False,
        )

    def _to_row(
        self,
        item: CanonicalContentItem,
        *,
        source_id: UUID,
        collection_run_id: UUID | None,
        source_seed_entry_id: UUID | None,
    ) -> dict[str, Any]:
        normalized = normalize_text(item.original_text)
        url = safe_url(item.canonical_url)
        title = normalize_text(item.title)
        excerpt = truncate_excerpt(normalize_text(item.permitted_excerpt), EXCERPT_CHARACTER_LIMIT)

        # No key configured means no retained original. Storing plaintext in a
        # column called `text_ciphertext` would mislead every later reader.
        ciphertext = (
            self._cipher.encrypt(item.original_text)
            if self._cipher is not None and item.original_text
            else None
        )

        return {
            "source_id": source_id,
            "source_item_id": item.source_item_id,
            "collection_run_id": collection_run_id,
            "source_seed_entry_id": source_seed_entry_id,
            "content_kind": item.content_kind,
            "canonical_url": url,
            "canonical_url_key": canonical_url_key(url) if url is not None else None,
            "headline_key": headline_key(publisher=item.publisher_or_container, title=item.title),
            "dataset_package_id": item.dataset.dataset_package_id if item.dataset else None,
            "dataset_import_run_id": (item.dataset.dataset_import_run_id if item.dataset else None),
            "dataset_row_id": item.dataset.dataset_row_id if item.dataset else None,
            "dataset_annotations": dict(item.dataset_annotations),
            "title": title,
            "permitted_excerpt": excerpt,
            "text_ciphertext": ciphertext,
            "normalized_text": normalized,
            "normalization_version": NORMALIZATION_VERSION,
            "normalized_context": assemble_context(item.context),
            "publisher_or_container": normalize_text(item.publisher_or_container),
            "published_at": item.published_at,
            "observed_at": item.observed_at or datetime.now(UTC),
            "language": normalize_language(item.language),
            "country_code": item.country_code,
            "geographic_scope": item.geographic_scope,
            "source_status": item.source_status,
            "is_fixture": item.is_fixture,
            "submitted_origin": item.submitted_origin,
            "content_hash": content_hash(
                source_key=item.source_key,
                content_kind=item.content_kind.value,
                normalized_text=normalized,
                title=title,
                canonical_url=url,
            ),
            "metadata": dict(item.provider_metadata),
        }
