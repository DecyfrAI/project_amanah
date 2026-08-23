"""Bounded news ingestion from the reviewed RSS allowlist (B-S9).

One adapter instance serves one outlet, and it collects from exactly the feeds
that outlet has approved seed entries for. There is no discovery of feeds: the
allowlist in `docs/news-rss-sources.md` was checked by hand on 23 August 2026,
the feeds it rejected are absent from configuration on purpose, and inventing a
replacement for one of them is prohibited.

What is stored is metadata plus a short permitted excerpt and a link back. The
adapter never requests the article itself, never reads `content:encoded`, and
never goes past a paywall. A feed that is unreachable becomes a **coverage
warning and a gap**, never a zero: `rules/backend.md` is explicit that missing
data must not be represented as an observation of nothing.

Relevance filtering is configuration, applied per feed. It selects subject
matter — religion, hate crime, public affairs — and drops the sport and celebrity
desks that share a general feed. An article that passes the filter is *on topic*;
whether it says anything hateful is a later, separate, staged decision, and no
classification is ever attached to an ingested article here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from amanah.canonical.text import truncate_excerpt
from amanah.canonical.urls import safe_url
from amanah.domain.enums import ContentKind, NewsScope
from amanah.ingestion.configuration import SeedConfig, SeedConfiguration, SourceConfiguration
from amanah.ingestion.contract import (
    AdapterError,
    BaseSourceAdapter,
    CanonicalContentItem,
    ContentContext,
    DiscoveryRequest,
    DiscoveryResult,
    FetchedPayload,
    SeedProvenance,
    SourceReference,
)
from amanah.ingestion.http import (
    ClientFactory,
    HttpLimits,
    http_client,
    raise_for_status,
    read_bounded,
)
from amanah.ingestion.news.feeds import parse_feed
from amanah.settings import Settings

logger = logging.getLogger(__name__)

ADAPTER_VERSION = "news-rss-1.0.0"

#: Reviewed feed terms permit a short excerpt. `docs/news-rss-sources.md`
#: recommends this length.
EXCERPT_CHARACTER_LIMIT = 400

#: English only for P0. A feed that declares another language, or an entry that
#: does, is skipped and counted rather than stored unevaluated.
MVP_LANGUAGE = "en"

#: Countries in scope, plus clearly global religion and hate-crime reporting.
IN_SCOPE_COUNTRIES = frozenset({"CA", "US", "GB"})

#: Configuration keys of every outlet in the reviewed allowlist. Derived from
#: configuration at import so adding an outlet is a configuration change rather
#: than a code change — but only an outlet that is *in* configuration can run.
NEWS_SOURCE_KEY_PREFIX = "rss_"


class NewsAdapter(BaseSourceAdapter):
    """Collects one outlet's approved feeds."""

    def __init__(
        self,
        *,
        source_key: str,
        seeds: tuple[SeedConfig, ...],
        limits: HttpLimits,
        homepage_url: str | None,
        outlet_name: str,
        client_factory: ClientFactory = http_client,
    ) -> None:
        super().__init__(source_key=source_key, adapter_version=ADAPTER_VERSION, is_fixture=False)
        self._seeds = seeds
        self._limits = limits
        self._homepage_url = homepage_url
        self._outlet_name = outlet_name
        self._client_factory = client_factory
        self._config_version = seeds[0].config_version if seeds else "unconfigured"

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Read every approved feed for this outlet and select what is in scope.

        Discovery does the whole retrieval: an RSS entry *is* the record, so a
        separate `fetch` against the publisher would be an extra request for
        content we are not allowed to store anyway.
        """
        if not self._seeds:
            raise AdapterError("no_approved_feeds", is_policy_block=True)

        references: list[SourceReference] = []
        warnings: list[str] = []
        counts = {
            "feeds_read": 0,
            "feeds_unavailable": 0,
            "discovered": 0,
            "skipped_off_topic": 0,
            "skipped_out_of_window": 0,
            "skipped_wrong_language": 0,
        }
        with self._client_factory(self._limits) as client:
            for seed in self._seeds:
                if len(references) >= request.item_cap:
                    warnings.append(
                        "The item cap was reached before every approved feed was read, "
                        "so this run covers part of the window only."
                    )
                    break
                try:
                    response = read_bounded(client, seed.provider_reference, limits=self._limits)
                    raise_for_status(response)
                    feed = parse_feed(response.content)
                except AdapterError as exc:
                    # One unreachable feed is a gap in this outlet's coverage, not
                    # a failed run: the other feeds still have something to say.
                    counts["feeds_unavailable"] += 1
                    warnings.append(
                        f"{seed.display_name} could not be read for this window, "
                        "so its coverage is missing rather than empty."
                    )
                    logger.warning(
                        "news feed unavailable",
                        extra={"registry_key": seed.registry_key, "safe_code": exc.safe_code},
                    )
                    continue

                counts["feeds_read"] += 1
                for entry in feed.entries:
                    if len(references) >= request.item_cap:
                        break
                    language = entry.language or feed.language or MVP_LANGUAGE
                    if not language.lower().startswith(MVP_LANGUAGE):
                        counts["skipped_wrong_language"] += 1
                        continue
                    if _outside_window(entry.published_at, request):
                        counts["skipped_out_of_window"] += 1
                        continue
                    if seed.topical_filter is not None and not seed.topical_filter.matches(
                        entry.title, entry.summary
                    ):
                        counts["skipped_off_topic"] += 1
                        continue

                    url = safe_url(entry.link)
                    if url is None:
                        continue
                    reference = SourceReference(
                        reference_id=entry.entry_id,
                        content_kind=ContentKind.news_article,
                        hint={
                            "url": url,
                            "title": entry.title,
                            "summary": entry.summary,
                            "published_at": (
                                entry.published_at.isoformat() if entry.published_at else None
                            ),
                            "language": MVP_LANGUAGE,
                            "country_scope": seed.country_scope,
                        },
                        seed=_seed_provenance(seed),
                    )
                    references.append(reference)

        counts["discovered"] = len(references)
        return DiscoveryResult(
            references=tuple(references),
            # Feeds are a sliding window of recent items with no stable pagination
            # token, so there is nothing honest to resume from. The window and the
            # database dedupe keys do that work instead.
            cursor=None,
            coverage_warnings=tuple(dict.fromkeys(warnings)),
            counts=counts,
        )

    def fetch(self, reference: SourceReference) -> FetchedPayload:
        """Return what discovery already read; no second request is made.

        The permitted fields travel on the reference itself, so this stage does
        not reach back to the publisher for content the licence would not let us
        store anyway. One request per feed, not one per article.
        """
        hint: dict[str, Any] = dict(reference.hint)
        if not hint:
            raise AdapterError("news_entry_missing", is_retryable=False)
        return FetchedPayload(reference=reference, payload=hint, retrieved_at=datetime.now(UTC))

    def canonicalize(self, payload: FetchedPayload) -> CanonicalContentItem:
        hint = payload.payload
        published_at = hint.get("published_at")
        country = hint.get("country_scope")
        return CanonicalContentItem(
            source_key=self.source_key,
            source_item_id=payload.reference.reference_id,
            content_kind=ContentKind.news_article,
            observed_at=payload.retrieved_at,
            is_fixture=False,
            canonical_url=hint.get("url"),
            title=hint.get("title"),
            permitted_excerpt=truncate_excerpt(hint.get("summary"), EXCERPT_CHARACTER_LIMIT),
            # No `original_text`. The product stores an excerpt and a link, never
            # the article, so there is nothing to retain and nothing to encrypt.
            original_text=None,
            publisher_or_container=self._outlet_name,
            published_at=datetime.fromisoformat(published_at) if published_at else None,
            language=MVP_LANGUAGE,
            country_code=country if country in IN_SCOPE_COUNTRIES else None,
            geographic_scope=(
                NewsScope.local.value if country in IN_SCOPE_COUNTRIES else NewsScope.globally.value
            ),
            context=ContentContext(title=hint.get("title")),
            seed=payload.reference.seed,
            provider_metadata={"homepage_url": self._homepage_url} if self._homepage_url else {},
        )


def _seed_provenance(seed: SeedConfig) -> SeedProvenance:
    return SeedProvenance(
        registry_key=seed.registry_key,
        config_version=seed.config_version,
        query_family=seed.query_family,
        query_purpose=seed.query_purpose,
        sampling_stratum=seed.sampling_stratum,
        item_cap=seed.item_cap,
        language=seed.language,
    )


def _outside_window(published: datetime | None, request: DiscoveryRequest) -> bool:
    """An entry with no publication date is kept rather than silently dropped."""
    if published is None:
        return False
    if request.window_start is not None and published < request.window_start:
        return True
    return request.window_end is not None and published > request.window_end


def news_source_keys(sources: SourceConfiguration) -> tuple[str, ...]:
    """Configured outlet keys, so the registry does not hard-code a list."""
    return tuple(
        source.source_key
        for source in sources.sources
        if source.source_key.startswith(NEWS_SOURCE_KEY_PREFIX)
    )


def build_news_adapter(
    source_key: str,
    settings: Settings,
    sources: SourceConfiguration,
    seeds: SeedConfiguration,
) -> NewsAdapter:
    """Build the adapter for one outlet from reviewed configuration."""
    configured = sources.by_key(source_key)
    if configured is None:
        raise AdapterError("source_not_configured", is_policy_block=True)
    return NewsAdapter(
        source_key=source_key,
        seeds=seeds.runnable_for(source_key),
        limits=HttpLimits.from_settings(settings),
        homepage_url=configured.homepage_url,
        outlet_name=configured.name,
    )
