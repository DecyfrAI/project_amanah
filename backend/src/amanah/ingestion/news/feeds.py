"""Parsing reviewed RSS and Atom feeds (B-S9.2, B-S9.3).

A feed is hostile input. It arrives as XML from a third party, so it is parsed
with `defusedxml`: entity expansion and external entity resolution are the two
classic ways a small document becomes a denial of service or a file read, and the
standard library's parser defends against neither.

What is extracted is deliberately narrow. `docs/news-rss-sources.md` and
`spec.md` section 10.5 permit headline, publisher, canonical link, a short
excerpt, publication time, and language — nothing else. `content:encoded` carries
the full article in several of these feeds and is **never** read: storing it
would be republication, which every licence note in the allowlist forbids.

HTML inside a description is stripped to plain text rather than sanitized and
kept. There is no case in this product where provider markup should reach a
database column, let alone a browser.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import ParseError, fromstring

from amanah.ingestion.contract import AdapterError

#: XML namespaces the reviewed feeds actually use.
_ATOM = "{http://www.w3.org/2005/Atom}"
_DUBLIN_CORE = "{http://purl.org/dc/elements/1.1/}"

_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

#: Cap on entries taken from one feed document, independent of the run's item
#: cap. A feed that suddenly returns ten thousand entries is a provider fault,
#: not an opportunity.
MAXIMUM_ENTRIES_PER_FEED = 200


@dataclass(frozen=True, slots=True)
class FeedEntry:
    """One entry, reduced to the fields the licence permits us to keep."""

    entry_id: str
    title: str | None
    link: str | None
    summary: str | None
    published_at: datetime | None
    language: str | None


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    """One parsed feed document."""

    title: str | None
    language: str | None
    entries: tuple[FeedEntry, ...]


def strip_markup(value: str | None) -> str | None:
    """Reduce a description to plain text.

    Tags are removed rather than escaped, and the handful of entities these feeds
    actually use are decoded, so what is stored reads as a sentence instead of as
    markup a later renderer might be tempted to trust.
    """
    if value is None:
        return None
    text = _TAG_PATTERN.sub(" ", value)
    for entity, character in (
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
        ("&apos;", "'"),
    ):
        text = text.replace(entity, character)
    collapsed = _WHITESPACE.sub(" ", text).strip()
    return collapsed or None


def parse_feed(document: bytes) -> ParsedFeed:
    """Parse an RSS 2.0 or Atom document, or refuse it.

    A malformed feed is a permanent failure for this attempt rather than a
    retryable one: the same bytes will not parse on a second try, and the run
    records it as a coverage gap for that feed alone.
    """
    try:
        root = fromstring(document)
    except (ParseError, ValueError) as exc:
        raise AdapterError("feed_malformed", is_retryable=False) from exc

    if root.tag == f"{_ATOM}feed":
        return _parse_atom(root)
    channel = root.find("channel")
    if channel is not None:
        return _parse_rss(channel)
    raise AdapterError("feed_format_unsupported", is_retryable=False)


def _text(element: Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _parse_rss(channel: Element) -> ParsedFeed:
    language = _text(channel.find("language"))
    entries = tuple(_rss_entries(channel, language))
    return ParsedFeed(title=_text(channel.find("title")), language=language, entries=entries)


def _rss_entries(channel: Element, feed_language: str | None) -> Iterator[FeedEntry]:
    for index, item in enumerate(channel.findall("item")):
        if index >= MAXIMUM_ENTRIES_PER_FEED:
            return
        link = _text(item.find("link"))
        # `description` only. `content:encoded` is the full article body and is
        # deliberately not read: every licence note in the allowlist permits a
        # short excerpt and a link, and nothing more.
        summary = strip_markup(_text(item.find("description")))
        guid = _text(item.find("guid")) or link
        if guid is None:
            continue
        yield FeedEntry(
            entry_id=guid,
            title=_text(item.find("title")),
            link=link,
            summary=summary,
            published_at=_parse_date(
                _text(item.find("pubDate")) or _text(item.find(f"{_DUBLIN_CORE}date"))
            ),
            language=feed_language,
        )


def _parse_atom(feed: Element) -> ParsedFeed:
    language = feed.get("{http://www.w3.org/XML/1998/namespace}lang")
    entries = tuple(_atom_entries(feed, language))
    return ParsedFeed(title=_text(feed.find(f"{_ATOM}title")), language=language, entries=entries)


def _atom_entries(feed: Element, feed_language: str | None) -> Iterator[FeedEntry]:
    for index, entry in enumerate(feed.findall(f"{_ATOM}entry")):
        if index >= MAXIMUM_ENTRIES_PER_FEED:
            return
        link = _atom_link(entry)
        entry_id = _text(entry.find(f"{_ATOM}id")) or link
        if entry_id is None:
            continue
        # Atom `summary`, never `content`: same reason as RSS `description`.
        yield FeedEntry(
            entry_id=entry_id,
            title=_text(entry.find(f"{_ATOM}title")),
            link=link,
            summary=strip_markup(_text(entry.find(f"{_ATOM}summary"))),
            published_at=_parse_date(
                _text(entry.find(f"{_ATOM}published")) or _text(entry.find(f"{_ATOM}updated"))
            ),
            language=feed_language,
        )


def _atom_link(entry: Element) -> str | None:
    """The alternate link, which is the article a reader should reach."""
    fallback: str | None = None
    for link in entry.findall(f"{_ATOM}link"):
        href = link.get("href")
        if href is None:
            continue
        if link.get("rel", "alternate") == "alternate":
            return href
        fallback = fallback or href
    return fallback


def _parse_date(value: object) -> datetime | None:
    """Read RFC 2822 or ISO-8601, and return `None` when neither works.

    An unreadable date leaves `published_at` null rather than defaulting to the
    retrieval time: "we do not know when this was published" and "this was
    published the moment we saw it" are different claims, and only one is true.
    """
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
