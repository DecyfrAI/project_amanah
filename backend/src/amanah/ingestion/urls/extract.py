"""Metadata extraction from a retrieved page (B-S11.5).

Deliberately small. This reads a title, a description, a canonical link, a
publisher name, and a publication date out of a bounded byte string using the
standard library's HTML parser. It executes nothing, follows nothing, and loads
no external resource: a page is untrusted input, and the safest parser is the one
that cannot do anything but parse.

It does **not** extract article bodies. `spec.md` section 10.5 permits metadata
and a short excerpt; taking the body would be republication, and doing it from a
page a user pointed at would be republication we were asked to perform.

Everything is optional. A page with no description yields `description=None`, not
a guess assembled from the first paragraph — a fabricated summary is worse than
an absent one, because it looks like the publisher wrote it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from html.parser import HTMLParser

from amanah.canonical.text import normalize_text, truncate_excerpt
from amanah.canonical.urls import safe_url

logger = logging.getLogger(__name__)

#: Cap on the excerpt taken from a page description.
DESCRIPTION_CHARACTER_LIMIT = 400

#: How much of a document is parsed. A page longer than this is truncated before
#: parsing: everything worth reading lives in `<head>`, and parsing megabytes of
#: body to find it would be work done on an attacker's behalf.
PARSE_BUDGET_BYTES = 512 * 1024

#: `meta` names and properties worth reading, mapped onto our own field names.
_DESCRIPTION_KEYS = frozenset({"description", "og:description", "twitter:description"})
_TITLE_KEYS = frozenset({"og:title", "twitter:title"})
_SITE_KEYS = frozenset({"og:site_name", "application-name"})
_PUBLISHED_KEYS = frozenset(
    {"article:published_time", "datepublished", "date", "og:published_time"}
)


@dataclass(frozen=True, slots=True)
class PageMetadata:
    """What a retrieved page told us about itself."""

    title: str | None = None
    description: str | None = None
    canonical_url: str | None = None
    site_name: str | None = None
    published_at_text: str | None = None
    language: str | None = None


class _MetadataParser(HTMLParser):
    """Collects head metadata and stops caring once the body starts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.description: str | None = None
        self.og_title: str | None = None
        self.canonical_url: str | None = None
        self.site_name: str | None = None
        self.published_at_text: str | None = None
        self.language: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}
        if tag == "html":
            self.language = attributes.get("lang") or None
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._read_meta(attributes)
        elif tag == "link" and attributes.get("rel", "").lower() == "canonical":
            self.canonical_url = attributes.get("href") or None

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and self.title is None:
            stripped = data.strip()
            self.title = stripped or None

    def _read_meta(self, attributes: dict[str, str]) -> None:
        key = (attributes.get("property") or attributes.get("name") or "").lower()
        content = attributes.get("content", "").strip()
        if not key or not content:
            return
        if key in _DESCRIPTION_KEYS and self.description is None:
            self.description = content
        elif key in _TITLE_KEYS and self.og_title is None:
            self.og_title = content
        elif key in _SITE_KEYS and self.site_name is None:
            self.site_name = content
        elif key in _PUBLISHED_KEYS and self.published_at_text is None:
            self.published_at_text = content


def extract_metadata(content: bytes, *, url: str) -> PageMetadata:
    """Read permitted metadata out of a retrieved document.

    Decoding replaces undecodable bytes rather than failing: a page with a
    mislabelled charset should yield imperfect metadata, not an error that hides
    an otherwise usable submission.
    """
    document = content[:PARSE_BUDGET_BYTES].decode("utf-8", errors="replace")
    parser = _MetadataParser()
    try:
        parser.feed(document)
    except Exception as exc:
        # A page that breaks the parser still produced whatever was read before
        # the break, and partial metadata beats discarding the submission. The
        # page itself is never logged, only the fact that parsing stopped.
        logger.info("page metadata parsing stopped early", exc_info=exc)
    finally:
        parser.close()

    canonical = safe_url(parser.canonical_url) if parser.canonical_url else None
    return PageMetadata(
        title=normalize_text(parser.og_title or parser.title),
        description=truncate_excerpt(
            normalize_text(parser.description), DESCRIPTION_CHARACTER_LIMIT
        ),
        canonical_url=canonical or safe_url(url),
        site_name=normalize_text(parser.site_name),
        published_at_text=parser.published_at_text,
        language=parser.language,
    )
