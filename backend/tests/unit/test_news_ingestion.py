"""Bounded news ingestion (B-S9.6).

Provider HTTP is mocked at the transport, which is the only external boundary
here: feed parsing, topical filtering, language gating, windowing, and
canonicalization all run for real. That is what makes a malformed-feed or
outage case meaningful — the same code path runs as in production, with a
different set of bytes arriving.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import httpx2
import pytest

from amanah.canonical.store import EXCERPT_CHARACTER_LIMIT
from amanah.domain.enums import (
    ApprovalStatus,
    ContentKind,
    NewsScope,
    SamplingStratum,
    SeedEntryKind,
)
from amanah.ingestion.configuration import SeedConfig, TopicalFilter
from amanah.ingestion.contract import AdapterError, DiscoveryRequest
from amanah.ingestion.http import ClientFactory, HttpLimits
from amanah.ingestion.news.adapter import NewsAdapter
from amanah.ingestion.news.feeds import parse_feed, strip_markup

FEED_URL = "https://feeds.example.test/news.xml"

LIMITS = HttpLimits(
    connect_timeout_seconds=1.0,
    read_timeout_seconds=1.0,
    total_timeout_seconds=2.0,
    max_response_bytes=1_000_000,
)


def _rss(items: str, language: str = "en-gb") -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>Synthetic Wire</title>"
        f"<language>{language}</language>"
        f"{items}"
        "</channel></rss>"
    ).encode()


def _item(
    *,
    title: str,
    link: str,
    description: str = "A short synthetic description.",
    published: str = "Mon, 20 Jul 2026 09:15:00 GMT",
    guid: str | None = None,
) -> str:
    identifier = guid or link
    return (
        "<item>"
        f"<title>{title}</title>"
        f"<link>{link}</link>"
        f"<description>{description}</description>"
        f"<pubDate>{published}</pubDate>"
        f"<guid>{identifier}</guid>"
        "</item>"
    )


def _seed(**overrides: object) -> SeedConfig:
    values: dict[str, object] = {
        "registry_key": "rss_synthetic.headlines",
        "source_key": "rss_synthetic",
        "entry_kind": SeedEntryKind.feed,
        "display_name": "Synthetic Wire (headlines)",
        "provider_reference": FEED_URL,
        "query_family": "reviewed_news_feed",
        "query_purpose": "Public-affairs coverage for the monitored window.",
        "sampling_stratum": SamplingStratum.ordinary_monitoring,
        "language": "en",
        "country_scope": "GB",
        "item_cap": 50,
        "approval_status": ApprovalStatus.approved,
        "approved_by": "reviewer",
        "config_version": "test-1",
        "topical_filter": TopicalFilter(
            keep_terms=("mosque", "hate crime", "council"), drop_terms=("football",)
        ),
    }
    values.update(overrides)
    return SeedConfig.model_validate(values)


def _client_factory(handler: Callable[[httpx2.Request], httpx2.Response]) -> ClientFactory:
    """Bind a mock transport into the injectable client seam.

    Only the transport is replaced. Feed parsing, filtering, language gating,
    windowing, and canonicalization all run for real, which is what makes an
    outage or malformed-feed case say anything.
    """
    transport = httpx2.MockTransport(handler)

    @contextmanager
    def factory(limits: HttpLimits) -> Iterator[httpx2.Client]:
        del limits
        client = httpx2.Client(transport=transport, follow_redirects=False)
        try:
            yield client
        finally:
            client.close()

    return factory


def _adapter(
    handler: Callable[[httpx2.Request], httpx2.Response],
    seeds: tuple[SeedConfig, ...] | None = None,
) -> NewsAdapter:
    return NewsAdapter(
        source_key="rss_synthetic",
        seeds=seeds if seeds is not None else (_seed(),),
        limits=LIMITS,
        homepage_url="https://example.test",
        outlet_name="Synthetic Wire",
        client_factory=_client_factory(handler),
    )


# -- feed parsing ---------------------------------------------------------


def test_html_in_a_description_is_reduced_to_plain_text() -> None:
    """No provider markup reaches a database column, let alone a browser."""
    assert strip_markup("<p>Some <b>bold</b> text &amp; more</p>") == "Some bold text & more"


def test_an_rss_feed_yields_its_entries() -> None:
    feed = parse_feed(_rss(_item(title="Council debates", link="https://example.test/a")))

    assert feed.language == "en-gb"
    assert len(feed.entries) == 1
    assert feed.entries[0].title == "Council debates"
    assert feed.entries[0].published_at is not None


def test_an_atom_feed_yields_its_entries() -> None:
    document = (
        b'<?xml version="1.0" encoding="utf-8"?>'
        b'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">'
        b"<title>Synthetic Atom</title>"
        b"<entry>"
        b"<id>tag:example.test,2026:1</id>"
        b"<title>Mosque safety debated</title>"
        b'<link rel="alternate" href="https://example.test/atom-a"/>'
        b"<summary>A short synthetic summary.</summary>"
        b"<published>2026-07-20T09:15:00Z</published>"
        b"</entry></feed>"
    )

    feed = parse_feed(document)

    assert feed.entries[0].link == "https://example.test/atom-a"
    assert feed.entries[0].title == "Mosque safety debated"


def test_a_malformed_feed_is_a_permanent_failure() -> None:
    """The same bytes will not parse on a second attempt, so retrying is waste."""
    with pytest.raises(AdapterError) as raised:
        parse_feed(b"<rss><channel><item><title>unclosed")

    assert raised.value.is_retryable is False


def test_an_unrecognised_document_is_refused() -> None:
    with pytest.raises(AdapterError):
        parse_feed(b'<?xml version="1.0"?><html><body>not a feed</body></html>')


def test_an_unreadable_publication_date_leaves_the_field_null() -> None:
    """ "We do not know when this was published" and "it was published when we
    saw it" are different claims."""
    feed = parse_feed(
        _rss(_item(title="Mosque safety", link="https://example.test/a", published="nonsense"))
    )

    assert feed.entries[0].published_at is None


def test_the_full_article_body_is_never_read() -> None:
    """`content:encoded` carries the whole article; storing it is republication,
    which every licence note in the allowlist forbids."""
    document = _rss(
        "<item>"
        "<title>Mosque safety</title>"
        "<link>https://example.test/a</link>"
        "<description>A short synthetic description.</description>"
        "<content:encoded "
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">'
        "THE ENTIRE ARTICLE BODY"
        "</content:encoded>"
        "</item>"
    )

    feed = parse_feed(document)

    assert "ENTIRE ARTICLE BODY" not in (feed.entries[0].summary or "")


# -- the adapter ----------------------------------------------------------


def _responder(body: bytes, status: int = 200) -> Callable[[httpx2.Request], httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(status, content=body)

    return handler


def test_on_topic_articles_are_kept_and_off_topic_ones_are_dropped() -> None:
    """B-S9.7. The filter selects subject matter; it is not a harm signal."""
    body = _rss(
        _item(title="Council debates mosque safety", link="https://example.test/keep")
        + _item(title="Football transfer roundup", link="https://example.test/drop")
    )
    adapter = _adapter(_responder(body))

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    assert [reference.reference_id for reference in result.references] == [
        "https://example.test/keep"
    ]
    assert result.counts["skipped_off_topic"] == 1


def test_neutral_reporting_about_muslims_stays_in_scope() -> None:
    """Muslim-related vocabulary means an article is on topic, never that it is
    hateful, and the adapter attaches no classification of any kind."""
    body = _rss(
        _item(
            title="Mosque opens community food bank",
            link="https://example.test/neutral",
            description="A neutral report about a local mosque.",
        )
    )
    adapter = _adapter(_responder(body))

    result = adapter.discover(DiscoveryRequest(item_cap=50))
    item = adapter.canonicalize(adapter.fetch(result.references[0]))

    assert item.content_kind is ContentKind.news_article
    # There is nowhere on a canonical item to record a hate label, and nothing
    # here invents one.
    assert not hasattr(item, "relevance")
    assert not hasattr(item, "stance")


def test_a_non_english_feed_is_skipped_for_the_english_only_mvp() -> None:
    body = _rss(
        _item(title="Conseil municipal et mosquee", link="https://example.test/fr"),
        language="fr",
    )
    adapter = _adapter(_responder(body))

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    assert result.references == ()
    assert result.counts["skipped_wrong_language"] == 1


def test_articles_outside_the_window_are_skipped() -> None:
    body = _rss(
        _item(
            title="Council debates mosque safety",
            link="https://example.test/old",
            published="Mon, 01 Jan 2024 09:15:00 GMT",
        )
    )
    adapter = _adapter(_responder(body))

    result = adapter.discover(
        DiscoveryRequest(
            item_cap=50,
            window_start=datetime(2026, 7, 1, tzinfo=UTC),
            window_end=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )

    assert result.counts["skipped_out_of_window"] == 1


def test_the_item_cap_is_respected() -> None:
    body = _rss(
        "".join(
            _item(
                title=f"Council debates mosque item {index}", link=f"https://example.test/{index}"
            )
            for index in range(10)
        )
    )
    adapter = _adapter(_responder(body))

    result = adapter.discover(DiscoveryRequest(item_cap=3))

    assert len(result.references) == 3


def test_an_outage_becomes_a_coverage_gap_rather_than_a_zero() -> None:
    """B-S9.6. `rules/backend.md`: missing data must not read as an observation
    of nothing."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("unreachable", request=request)

    adapter = _adapter(handler)

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    assert result.references == ()
    assert result.counts["feeds_unavailable"] == 1
    assert result.coverage_warnings
    assert "missing rather than empty" in result.coverage_warnings[0]


def test_a_rate_limited_feed_is_a_gap_for_that_feed_only() -> None:
    """One failing feed must not fail the outlet's other feeds."""
    healthy = _seed(registry_key="rss_synthetic.ok", provider_reference=FEED_URL)
    broken = _seed(
        registry_key="rss_synthetic.broken",
        provider_reference="https://feeds.example.test/broken.xml",
        display_name="Synthetic Wire (broken)",
    )

    def handler(request: httpx2.Request) -> httpx2.Response:
        if "broken" in str(request.url):
            return httpx2.Response(429, content=b"")
        return httpx2.Response(
            200,
            content=_rss(
                _item(title="Council debates mosque safety", link="https://example.test/keep")
            ),
        )

    adapter = _adapter(handler, seeds=(broken, healthy))

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    assert len(result.references) == 1
    assert result.counts["feeds_unavailable"] == 1
    assert result.counts["feeds_read"] == 1


def test_a_partial_feed_yields_what_it_could_parse() -> None:
    """One entry missing a link is dropped; the rest of the feed still counts."""
    body = _rss(
        _item(title="Council debates mosque safety", link="https://example.test/ok")
        + "<item><title>Hate crime figures</title><description>No link.</description></item>"
    )
    adapter = _adapter(_responder(body))

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    assert len(result.references) == 1


def test_the_same_article_from_two_feeds_yields_one_dedupe_key() -> None:
    """B-S9.4. The database enforces this; the adapter must not defeat it by
    emitting URLs that differ only by tracking parameters."""
    from amanah.canonical.urls import canonical_url_key

    body_one = _rss(
        _item(
            title="Council debates mosque safety",
            link="https://www.example.test/story/?utm_source=feed",
            guid="one",
        )
    )
    body_two = _rss(
        _item(title="Council debates mosque safety", link="https://example.test/story", guid="two")
    )

    first = _adapter(_responder(body_one)).discover(DiscoveryRequest(item_cap=5))
    second = _adapter(_responder(body_two)).discover(DiscoveryRequest(item_cap=5))

    keys = {
        canonical_url_key(str(first.references[0].hint["url"])),
        canonical_url_key(str(second.references[0].hint["url"])),
    }
    assert len(keys) == 1


def test_canonicalization_stores_metadata_and_an_excerpt_only() -> None:
    """`spec.md` section 10.5: headline, publisher, link, short excerpt — and no
    article body."""
    body = _rss(
        _item(
            title="Council debates mosque safety",
            link="https://example.test/story",
            description="A short synthetic description of the debate.",
        )
    )
    adapter = _adapter(_responder(body))
    result = adapter.discover(DiscoveryRequest(item_cap=5))

    item = adapter.canonicalize(adapter.fetch(result.references[0]))

    assert item.title == "Council debates mosque safety"
    assert item.publisher_or_container == "Synthetic Wire"
    assert item.canonical_url == "https://example.test/story"
    assert item.original_text is None
    assert item.permitted_excerpt is not None
    assert len(item.permitted_excerpt) <= EXCERPT_CHARACTER_LIMIT + 1
    assert item.is_fixture is False


def test_a_monitored_country_is_local_and_everything_else_is_global() -> None:
    body = _rss(_item(title="Council debates mosque safety", link="https://example.test/story"))

    local = _adapter(_responder(body))
    result = local.discover(DiscoveryRequest(item_cap=5))
    assert local.canonicalize(local.fetch(result.references[0])).geographic_scope == (
        NewsScope.local.value
    )

    worldwide = _adapter(_responder(body), seeds=(_seed(country_scope="global"),))
    result = worldwide.discover(DiscoveryRequest(item_cap=5))
    assert worldwide.canonicalize(worldwide.fetch(result.references[0])).geographic_scope == (
        NewsScope.globally.value
    )


def test_sampling_provenance_travels_with_every_article() -> None:
    body = _rss(_item(title="Council debates mosque safety", link="https://example.test/story"))
    adapter = _adapter(_responder(body))
    result = adapter.discover(DiscoveryRequest(item_cap=5))

    item = adapter.canonicalize(adapter.fetch(result.references[0]))

    assert item.seed is not None
    assert item.seed.registry_key == "rss_synthetic.headlines"
    assert item.seed.config_version == "test-1"
    assert item.seed.sampling_stratum is SamplingStratum.ordinary_monitoring


def test_an_outlet_with_no_approved_feed_is_a_policy_block() -> None:
    """An unreviewed entry stays inactive; that is governance, not a fault."""
    adapter = _adapter(_responder(b""), seeds=())

    with pytest.raises(AdapterError) as raised:
        adapter.discover(DiscoveryRequest(item_cap=5))

    assert raised.value.is_policy_block is True
