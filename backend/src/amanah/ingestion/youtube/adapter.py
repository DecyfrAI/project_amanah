"""Bounded YouTube collection from approved seeds and queries (B-S10).

The adapter runs only when two things are true: a server-side API key exists, and
at least one approved seed entry names something to collect. Neither implies the
other, and neither is inferred. With no key the connector reports `not_configured`
and nothing else in the product is affected; with no approved entry it is a policy
block, because `spec.md` section 10.3 says a registry entry stays inactive until
someone has reviewed it into versioned configuration.

Every item carries its sampling provenance — registry key, configuration version,
query family, query purpose, stratum, cap. That is not bookkeeping. The hackathon
seed sample is deliberately *enriched*: it was chosen to contain relevant material,
so a rate computed over it describes the sample and nothing else. Keeping the
stratum attached to every row is what stops it being pooled into a sentence that
sounds like prevalence.

Three coverage facts are recorded rather than swallowed: a video whose comments
are disabled, a thread whose replies the API did not return in full, and a run
that stopped because the day's quota was spent. Each is a gap. None is a zero.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from amanah.canonical.text import truncate_excerpt
from amanah.domain.enums import ConnectorStatus, ContentKind, SeedEntryKind
from amanah.ingestion.configuration import SeedConfig, SeedConfiguration, SourceConfiguration
from amanah.ingestion.contract import (
    AdapterCheckpoint,
    AdapterError,
    AdapterHealth,
    BaseSourceAdapter,
    CanonicalContentItem,
    ContentContext,
    DiscoveryRequest,
    DiscoveryResult,
    FetchedPayload,
    SeedProvenance,
    SourceReference,
)
from amanah.ingestion.http import ClientFactory, HttpLimits, http_client
from amanah.ingestion.youtube.client import (
    CommentsDisabledError,
    QuotaDeferredError,
    YouTubeClient,
)
from amanah.settings import Settings

logger = logging.getLogger(__name__)

YOUTUBE_SOURCE_KEY = "youtube"
ADAPTER_VERSION = "youtube-data-v3-1.0.0"

#: Excerpt length for a comment or a description. Long enough to read, short
#: enough that a single item cannot carry a document.
EXCERPT_CHARACTER_LIMIT = 1_000

#: Per-run ceilings, applied on top of whatever the seed's own cap allows. They
#: bound quota spend as much as storage.
MAXIMUM_VIDEOS_PER_SEED = 10
MAXIMUM_COMMENTS_PER_VIDEO = 100

#: Seed kinds this adapter knows how to run.
_SUPPORTED_ENTRY_KINDS = frozenset({SeedEntryKind.search_query, SeedEntryKind.seed_video})


class YouTubeAdapter(BaseSourceAdapter):
    """Collects videos and comments through the official Data API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        seeds: tuple[SeedConfig, ...],
        limits: HttpLimits,
        client_factory: ClientFactory = http_client,
    ) -> None:
        super().__init__(
            source_key=YOUTUBE_SOURCE_KEY, adapter_version=ADAPTER_VERSION, is_fixture=False
        )
        self._api_key = api_key
        self._seeds = tuple(seed for seed in seeds if seed.entry_kind in _SUPPORTED_ENTRY_KINDS)
        self._limits = limits
        self._client_factory = client_factory

    def health_check(self) -> AdapterHealth:
        """Report connector state without contacting the provider.

        A missing key and an empty approved seed list are different situations
        and are reported as such: one is a deployment gap, the other a governance
        one, and telling them apart is what makes the status actionable.
        """
        if self._api_key is None:
            return AdapterHealth(
                status=ConnectorStatus.not_configured,
                safe_warning="No API credential is configured, so YouTube is not collected.",
            )
        if not self._seeds:
            return AdapterHealth(
                status=ConnectorStatus.disabled,
                safe_warning="No approved seed or query is configured for this source.",
            )
        return AdapterHealth(status=ConnectorStatus.ok)

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Walk approved seeds, collecting videos and their comments under caps.

        Discovery does the retrieval because the expensive resource here is
        quota, not bandwidth: doing the work once and checkpointing is what lets
        an interrupted run resume rather than pay for the same pages again.
        """
        if self._api_key is None:
            raise AdapterError("connector_not_configured", is_policy_block=True)
        if not self._seeds:
            raise AdapterError("no_approved_seeds", is_policy_block=True)

        references: list[SourceReference] = []
        warnings: list[str] = []
        counts = {
            "videos_discovered": 0,
            "comments_discovered": 0,
            "videos_comments_disabled": 0,
            "videos_unavailable": 0,
            "replies_omitted": 0,
        }
        resume_after = request.cursor
        cursor: str | None = request.cursor
        deferred = False

        with self._client_factory(self._limits) as raw_client:
            client = YouTubeClient(api_key=self._api_key, client=raw_client, limits=self._limits)
            for seed in self._seeds:
                if resume_after is not None:
                    # Resume exactly where the last run stopped rather than
                    # re-spending quota on seeds already covered.
                    if seed.registry_key == resume_after:
                        resume_after = None
                    continue
                if len(references) >= request.item_cap or deferred:
                    break
                try:
                    collected = self._collect_seed(
                        client,
                        seed,
                        request,
                        item_cap=min(seed.item_cap, request.item_cap - len(references)),
                        counts=counts,
                        warnings=warnings,
                    )
                except QuotaDeferredError:
                    deferred = True
                    warnings.append(
                        "Collection stopped early because the provider quota for this day "
                        "was spent, so this window is covered in part only."
                    )
                    break
                references.extend(collected[: max(request.item_cap - len(references), 0)])
                cursor = seed.registry_key

        counts["videos_discovered"] = sum(
            1 for reference in references if reference.content_kind is ContentKind.social_post
        )
        counts["comments_discovered"] = sum(
            1 for reference in references if reference.content_kind is ContentKind.social_comment
        )
        return DiscoveryResult(
            references=tuple(references),
            cursor=cursor,
            coverage_warnings=tuple(dict.fromkeys(warnings)),
            counts=counts,
        )

    def _collect_seed(
        self,
        client: YouTubeClient,
        seed: SeedConfig,
        request: DiscoveryRequest,
        item_cap: int,
        counts: dict[str, int],
        warnings: list[str],
    ) -> list[SourceReference]:
        if item_cap <= 0:
            return []
        video_ids = self._video_ids(client, seed, request, item_cap=item_cap)
        provenance = _seed_provenance(seed)
        references: list[SourceReference] = []

        metadata = {
            str(item.get("id")): item for item in client.list_videos(tuple(video_ids)).items
        }
        for video_id in video_ids:
            if len(references) >= item_cap:
                break
            record = metadata.get(video_id)
            if record is None:
                # A seed video that has been removed is a coverage gap, not an
                # observation of a video with no comments.
                counts["videos_unavailable"] += 1
                warnings.append(
                    f"A seed video for {seed.display_name} was unavailable, so its "
                    "comments are missing rather than absent."
                )
                continue

            references.append(
                SourceReference(
                    reference_id=f"video:{video_id}",
                    content_kind=ContentKind.social_post,
                    hint={"kind": "video", "video": record},
                    seed=provenance,
                )
            )
            remaining = item_cap - len(references)
            if remaining > 0:
                references.extend(
                    self._comment_references(
                        client,
                        seed,
                        video_id,
                        record,
                        item_cap=remaining,
                        counts=counts,
                        warnings=warnings,
                    )
                )
        return references

    def _video_ids(
        self,
        client: YouTubeClient,
        seed: SeedConfig,
        request: DiscoveryRequest,
        *,
        item_cap: int,
    ) -> list[str]:
        if seed.entry_kind is SeedEntryKind.seed_video:
            return [seed.provider_reference]

        page = client.search_videos(
            query=seed.provider_reference,
            published_after=_iso(request.window_start),
            published_before=_iso(request.window_end),
            page_size=min(seed.item_cap, item_cap, MAXIMUM_VIDEOS_PER_SEED),
            relevance_language=seed.language,
        )
        found: list[str] = []
        for item in page.items:
            identifier = item.get("id")
            video_id = identifier.get("videoId") if isinstance(identifier, dict) else None
            if video_id:
                found.append(str(video_id))
            if len(found) >= MAXIMUM_VIDEOS_PER_SEED:
                break
        return found

    def _comment_references(
        self,
        client: YouTubeClient,
        seed: SeedConfig,
        video_id: str,
        video: Mapping[str, Any],
        item_cap: int,
        counts: dict[str, int],
        warnings: list[str],
    ) -> list[SourceReference]:
        provenance = _seed_provenance(seed)
        references: list[SourceReference] = []
        page_token: str | None = None
        comment_cap = min(item_cap, MAXIMUM_COMMENTS_PER_VIDEO)

        while len(references) < comment_cap:
            try:
                page = client.list_comment_threads(
                    video_id=video_id,
                    page_size=min(comment_cap - len(references), 50),
                    page_token=page_token,
                )
            except CommentsDisabledError:
                counts["videos_comments_disabled"] += 1
                warnings.append(
                    "Comments were disabled on at least one video in this window, so its "
                    "discussion is missing rather than empty."
                )
                return references

            for thread in page.items:
                if len(references) >= comment_cap:
                    break
                snippet = thread.get("snippet", {})
                top_level = snippet.get("topLevelComment", {})
                comment_id = str(top_level.get("id") or thread.get("id") or "")
                if not comment_id:
                    continue
                references.append(
                    SourceReference(
                        reference_id=f"comment:{comment_id}",
                        content_kind=ContentKind.social_comment,
                        hint={
                            "kind": "comment",
                            "comment": top_level,
                            "video": video,
                            "parent_id": None,
                        },
                        seed=provenance,
                    )
                )
                # The API returns only a sample of replies with a thread. The
                # difference between what it returned and what it says exists is
                # recorded, because a partial thread read as a whole one
                # undercounts every rate computed over it.
                declared = int(snippet.get("totalReplyCount") or 0)
                returned = len((thread.get("replies") or {}).get("comments") or [])
                if declared > returned:
                    counts["replies_omitted"] += declared - returned
                for reply in (thread.get("replies") or {}).get("comments") or []:
                    reply_id = str(reply.get("id") or "")
                    if not reply_id or len(references) >= comment_cap:
                        continue
                    references.append(
                        SourceReference(
                            reference_id=f"comment:{reply_id}",
                            content_kind=ContentKind.social_comment,
                            hint={
                                "kind": "comment",
                                "comment": reply,
                                "video": video,
                                "parent_id": comment_id,
                            },
                            seed=provenance,
                        )
                    )

            page_token = page.next_page_token
            if page_token is None:
                break

        if counts.get("replies_omitted"):
            warnings.append(
                "Some replies were not returned by the provider, so comment counts for "
                "this window are a lower bound."
            )
        return references

    def fetch(self, reference: SourceReference) -> FetchedPayload:
        """Return what discovery already retrieved; no second quota unit is spent."""
        hint: dict[str, Any] = dict(reference.hint)
        if not hint:
            raise AdapterError("youtube_reference_missing", is_retryable=False)
        return FetchedPayload(reference=reference, payload=hint, retrieved_at=datetime.now(UTC))

    def canonicalize(self, payload: FetchedPayload) -> CanonicalContentItem:
        hint = payload.payload
        video = hint.get("video") or {}
        video_snippet = video.get("snippet", {})
        video_title = video_snippet.get("title")

        if hint.get("kind") == "video":
            text = video_snippet.get("description")
            return self._item(
                payload,
                content_kind=ContentKind.social_post,
                text=text,
                title=video_title,
                published_at=_parse_time(video_snippet.get("publishedAt")),
                url=f"https://www.youtube.com/watch?v={video.get('id')}",
                context=ContentContext(title=video_title, caption=video_title),
            )

        comment_snippet = (hint.get("comment") or {}).get("snippet", {})
        return self._item(
            payload,
            content_kind=ContentKind.social_comment,
            # `textOriginal` rather than `textDisplay`: the display form contains
            # provider HTML, and no provider markup belongs in a stored column.
            text=comment_snippet.get("textOriginal"),
            title=None,
            published_at=_parse_time(comment_snippet.get("publishedAt")),
            url=f"https://www.youtube.com/watch?v={video.get('id')}",
            context=ContentContext(
                title=video_title,
                root_text=video_title,
                caption=video_snippet.get("description"),
            ),
        )

    def _item(
        self,
        payload: FetchedPayload,
        *,
        content_kind: ContentKind,
        text: str | None,
        title: str | None,
        published_at: datetime | None,
        url: str,
        context: ContentContext,
    ) -> CanonicalContentItem:
        seed = payload.reference.seed
        return CanonicalContentItem(
            source_key=self.source_key,
            source_item_id=payload.reference.reference_id,
            content_kind=content_kind,
            observed_at=payload.retrieved_at,
            is_fixture=False,
            canonical_url=url,
            title=title,
            permitted_excerpt=truncate_excerpt(text, EXCERPT_CHARACTER_LIMIT),
            original_text=text,
            publisher_or_container=(payload.payload.get("video") or {})
            .get("snippet", {})
            .get("channelTitle"),
            published_at=published_at,
            language=seed.language if seed else None,
            context=context,
            seed=seed,
            # No author identifier, no channel id, no display name: `spec.md`
            # section 18 forbids author search and identity resolution, and the
            # cheapest way to honour that is not to retain the identifier.
            provider_metadata={"query_purpose": seed.query_purpose} if seed else {},
        )

    def checkpoint(self, result: DiscoveryResult) -> AdapterCheckpoint:
        return AdapterCheckpoint(
            cursor=result.cursor,
            coverage_warnings=result.coverage_warnings,
            counts=dict(result.counts),
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


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _parse_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def build_youtube_adapter(
    settings: Settings, sources: SourceConfiguration, seeds: SeedConfiguration
) -> YouTubeAdapter:
    """Build the adapter from the environment and reviewed configuration."""
    del sources
    key = settings.youtube_api_key
    return YouTubeAdapter(
        api_key=key.get_secret_value() if key is not None else None,
        seeds=seeds.runnable_for(YOUTUBE_SOURCE_KEY),
        limits=HttpLimits.from_settings(settings),
    )
