"""Exact content hashes and deterministic identifiers (B-S12.5, B-S12.6).

Every value here is an *exact* hash, never a similarity signature.
`backend-implementation-plan.md` rules out speculative clustering for a reason:
"these two posts are 87% alike" is a research claim, and a pipeline that silently
merged near-duplicates would be making that claim on the product's behalf, in a
place nobody would look for it.

Fields are joined with a delimiter that cannot occur inside them, so
`("ab", "c")` and `("a", "bc")` cannot collide into the same digest.
"""

from __future__ import annotations

import hashlib

from amanah.canonical.text import normalize_text

#: A NUL byte cannot appear in a Postgres text column, so it cannot appear in any
#: of the values being joined.
_FIELD_SEPARATOR = "\x00"


def _digest(*parts: str) -> str:
    joined = _FIELD_SEPARATOR.join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def content_hash(
    *,
    source_key: str,
    content_kind: str,
    normalized_text: str | None,
    title: str | None = None,
    canonical_url: str | None = None,
) -> str:
    """Hash what the item *is*, so re-collecting it produces the same digest.

    Text is the primary input. Title and canonical URL join it because a news
    article often has no stored body at all — only a headline and a link — and a
    digest over an empty string would make every such article identical.
    """
    return _digest(
        source_key,
        content_kind,
        normalized_text or "",
        title or "",
        canonical_url or "",
    )


def headline_key(*, publisher: str | None, title: str | None) -> str | None:
    """The second news dedupe key: normalized publisher and headline.

    `spec.md` section 10.5 asks for it because the same story is often syndicated
    under different URLs. Case and whitespace are folded here — unlike in stored
    text — because this value is a key, never evidence.
    """
    if not publisher or not title:
        return None
    folded_publisher = (normalize_text(publisher) or "").casefold()
    folded_title = (normalize_text(title) or "").casefold()
    if not folded_publisher or not folded_title:
        return None
    return _digest(folded_publisher, folded_title)


def datapack_source_item_id(*, provider: str, name: str, version: str, row_id: str) -> str:
    """A stable, namespaced identifier for one row of one datapack version.

    `spec.md` section 14.6 asks for a deterministic namespaced value. Namespacing
    by package *and version* is what stops row `42` of two different datasets —
    or of two revisions of one dataset — from colliding into a single item.
    """
    return f"datapack:{_digest(provider, name, version, row_id)}"
