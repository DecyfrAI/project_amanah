"""Bounded YouTube collection (B-S10.8, B-S10.11).

The provider is replaced at the transport and nowhere else, so quota handling,
pagination, cap enforcement, stratum provenance, and the language gate all run
against the real adapter. Responses are hand-written in the shape the Data API
documents; nothing here was recorded from a live account.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest

from amanah.domain.enums import (
    ApprovalStatus,
    ConnectorStatus,
    ContentKind,
    SamplingStratum,
    SeedEntryKind,
)
from amanah.ingestion.configuration import SeedConfig
from amanah.ingestion.contract import AdapterError, DiscoveryRequest
from amanah.ingestion.http import ClientFactory, HttpLimits
from amanah.ingestion.youtube.adapter import MAXIMUM_COMMENTS_PER_VIDEO, YouTubeAdapter

LIMITS = HttpLimits(
    connect_timeout_seconds=1.0,
    read_timeout_seconds=1.0,
    total_timeout_seconds=2.0,
    max_response_bytes=1_000_000,
)


def _seed(**overrides: object) -> SeedConfig:
    values: dict[str, object] = {
        "registry_key": "youtube.seed.panel",
        "source_key": "youtube",
        "entry_kind": SeedEntryKind.seed_video,
        "display_name": "Synthetic panel discussion",
        "provider_reference": "vid-1",
        "query_family": "boundary_control",
        "query_purpose": "A control video used to check the classifier's false-positive rate.",
        "sampling_stratum": SamplingStratum.boundary_control,
        "language": "en",
        "country_scope": "GB",
        "item_cap": 5,
        "approval_status": ApprovalStatus.approved,
        "approved_by": "reviewer",
        "config_version": "test-1",
    }
    values.update(overrides)
    return SeedConfig.model_validate(values)


def _video(video_id: str = "vid-1") -> dict[str, Any]:
    return {
        "id": video_id,
        "snippet": {
            "title": "Panel discussion: reporting on faith communities",
            "description": "A recorded panel.",
            "channelTitle": "Synthetic Channel",
            "publishedAt": "2026-07-21T14:00:00Z",
        },
    }


def _thread(comment_id: str, text: str, *, replies: int = 0, returned: int = 0) -> dict[str, Any]:
    return {
        "id": comment_id,
        "snippet": {
            "topLevelComment": {
                "id": comment_id,
                "snippet": {"textOriginal": text, "publishedAt": "2026-07-21T15:00:00Z"},
            },
            "totalReplyCount": replies,
        },
        "replies": {
            "comments": [
                {
                    "id": f"{comment_id}.r{index}",
                    "snippet": {
                        "textOriginal": f"A reply {index}.",
                        "publishedAt": "2026-07-21T15:05:00Z",
                    },
                }
                for index in range(returned)
            ]
        },
    }


def _factory(handler: Callable[[httpx2.Request], httpx2.Response]) -> ClientFactory:
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
    *,
    api_key: str | None = "test-key",
    seeds: tuple[SeedConfig, ...] | None = None,
) -> YouTubeAdapter:
    return YouTubeAdapter(
        api_key=api_key,
        seeds=seeds if seeds is not None else (_seed(),),
        limits=LIMITS,
        client_factory=_factory(handler),
    )


def _json(payload: dict[str, Any], status: int = 200) -> httpx2.Response:
    return httpx2.Response(status, content=json.dumps(payload).encode())


def _standard(
    threads: list[dict[str, Any]] | None = None,
) -> Callable[[httpx2.Request], httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.endswith("/videos"):
            return _json({"items": [_video()]})
        if path.endswith("/commentThreads"):
            return _json({"items": threads if threads is not None else []})
        if path.endswith("/search"):
            return _json({"items": [{"id": {"videoId": "vid-1"}}]})
        return _json({"items": []})

    return handler


# -- configuration gating -------------------------------------------------


def test_a_missing_key_disables_only_this_connector() -> None:
    """`spec.md` section 17.2: `Not configured`, and everything else continues."""
    adapter = _adapter(_standard(), api_key=None)

    assert adapter.health_check().status is ConnectorStatus.not_configured
    with pytest.raises(AdapterError) as raised:
        adapter.discover(DiscoveryRequest(item_cap=5))
    assert raised.value.is_policy_block is True


def test_no_approved_seed_is_a_policy_block_not_a_failure() -> None:
    """An unreviewed registry entry stays inactive. That is governance."""
    adapter = _adapter(_standard(), seeds=())

    assert adapter.health_check().status is ConnectorStatus.disabled
    with pytest.raises(AdapterError) as raised:
        adapter.discover(DiscoveryRequest(item_cap=5))
    assert raised.value.is_policy_block is True


def test_an_unapproved_registry_entry_never_runs() -> None:
    """B-S10.11. Only entries projected into approved configuration may run."""
    pending = _seed(approval_status=ApprovalStatus.pending)

    assert pending.is_runnable is False


def test_a_non_english_entry_is_outside_the_mvp_scope() -> None:
    """`spec.md` section 10.3 keeps the French candidate disabled until the
    classifier and its evaluation set cover the language."""
    french = _seed(language="fr", approval_status=ApprovalStatus.approved)

    assert french.is_runnable is False


# -- discovery ------------------------------------------------------------


def test_a_seed_video_and_its_comments_are_collected() -> None:
    adapter = _adapter(_standard([_thread("c1", "A comment.")]))

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    kinds = [reference.content_kind for reference in result.references]
    assert ContentKind.social_post in kinds
    assert ContentKind.social_comment in kinds
    assert result.counts["videos_discovered"] == 1
    assert result.counts["comments_discovered"] == 1


def test_query_discovery_uses_the_official_search_endpoint() -> None:
    """No scraping path exists, so a query mode has to go through `search.list`."""
    seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.url.path)
        return _standard()(request)

    adapter = _adapter(
        handler,
        seeds=(_seed(entry_kind=SeedEntryKind.search_query, provider_reference="mosque safety"),),
    )
    adapter.discover(DiscoveryRequest(item_cap=10))

    assert any(path.endswith("/search") for path in seen)
    assert all("watch" not in path for path in seen)


def test_the_window_is_passed_to_the_provider() -> None:
    """An explicit date window is what keeps a backfill query bounded."""
    seen: list[httpx2.URL] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request.url)
        return _standard()(request)

    adapter = _adapter(
        handler, seeds=(_seed(entry_kind=SeedEntryKind.search_query, provider_reference="q"),)
    )
    adapter.discover(
        DiscoveryRequest(
            item_cap=10,
            window_start=datetime(2026, 7, 1, tzinfo=UTC),
            window_end=datetime(2026, 7, 31, tzinfo=UTC),
        )
    )

    search = next(url for url in seen if url.path.endswith("/search"))
    assert "publishedAfter" in str(search)
    assert "publishedBefore" in str(search)


def test_an_unavailable_seed_video_is_a_coverage_gap() -> None:
    """B-S10.5. Not an observation of a video with no comments."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/videos"):
            return _json({"items": []})
        return _standard()(request)

    result = _adapter(handler).discover(DiscoveryRequest(item_cap=50))

    assert result.counts["videos_unavailable"] == 1
    assert result.coverage_warnings
    assert "missing rather than absent" in result.coverage_warnings[0]


def test_disabled_comments_are_recorded_rather_than_read_as_silence() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/commentThreads"):
            return _json(
                {"error": {"errors": [{"reason": "commentsDisabled"}]}},
                status=403,
            )
        return _standard()(request)

    result = _adapter(handler).discover(DiscoveryRequest(item_cap=50))

    assert result.counts["videos_comments_disabled"] == 1
    assert any("missing rather than empty" in warning for warning in result.coverage_warnings)


def test_omitted_replies_are_counted_so_totals_are_a_lower_bound() -> None:
    """A thread declaring ten replies and returning two is partial, and a partial
    thread read as a whole one undercounts every rate over it."""
    adapter = _adapter(_standard([_thread("c1", "A comment.", replies=10, returned=2)]))

    result = adapter.discover(DiscoveryRequest(item_cap=50))

    assert result.counts["replies_omitted"] == 8
    assert any("lower bound" in warning for warning in result.coverage_warnings)


def test_quota_exhaustion_defers_and_reports_a_gap() -> None:
    """`spec.md` section 17.2: stop, checkpoint, and say the window is partial."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        return _json({"error": {"errors": [{"reason": "quotaExceeded"}]}}, status=403)

    result = _adapter(handler).discover(DiscoveryRequest(item_cap=50))

    assert result.references == ()
    assert any("quota" in warning for warning in result.coverage_warnings)


def test_a_revoked_key_is_a_policy_block_rather_than_a_retry_loop() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return _json({"error": {"errors": [{"reason": "forbidden"}]}}, status=403)

    with pytest.raises(AdapterError) as raised:
        _adapter(handler).discover(DiscoveryRequest(item_cap=50))

    assert raised.value.is_policy_block is True


def test_pagination_stops_at_the_comment_cap() -> None:
    """Without a cap, a video with a hundred thousand comments would collect all
    of them and spend the quota doing it."""
    pages: list[str | None] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.endswith("/commentThreads"):
            pages.append(request.url.params.get("pageToken"))
            return _json(
                {
                    "items": [
                        _thread(f"c{len(pages)}-{index}", "A comment.") for index in range(50)
                    ],
                    "nextPageToken": f"page-{len(pages)}",
                }
            )
        return _standard()(request)

    result = _adapter(handler, seeds=(_seed(item_cap=10_000),)).discover(
        DiscoveryRequest(item_cap=10_000)
    )

    comments = [
        reference
        for reference in result.references
        if reference.content_kind is ContentKind.social_comment
    ]
    assert len(comments) <= MAXIMUM_COMMENTS_PER_VIDEO
    assert len(pages) > 1


def test_seed_item_cap_is_applied_before_comment_pagination() -> None:
    paths: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        paths.append(request.url.path)
        return _standard([_thread("c1", "A comment.")])(request)

    result = _adapter(handler, seeds=(_seed(item_cap=1),)).discover(DiscoveryRequest(item_cap=50))

    assert len(result.references) == 1
    assert result.references[0].content_kind is ContentKind.social_post
    assert not any(path.endswith("/commentThreads") for path in paths)


def test_remaining_run_cap_is_applied_before_comment_pagination() -> None:
    paths: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        paths.append(request.url.path)
        return _standard([_thread("c1", "A comment.")])(request)

    result = _adapter(handler, seeds=(_seed(item_cap=100),)).discover(DiscoveryRequest(item_cap=1))

    assert len(result.references) == 1
    assert not any(path.endswith("/commentThreads") for path in paths)


def test_a_resumed_run_skips_the_seed_it_already_covered() -> None:
    """Re-spending quota on finished seeds is the expensive kind of bug."""
    first = _seed(registry_key="youtube.seed.one", provider_reference="vid-1")
    second = _seed(registry_key="youtube.seed.two", provider_reference="vid-2")
    adapter = _adapter(_standard(), seeds=(first, second))

    resumed = adapter.discover(DiscoveryRequest(item_cap=50, cursor="youtube.seed.one"))

    assert all(
        reference.seed is not None and reference.seed.registry_key == "youtube.seed.two"
        for reference in resumed.references
    )


# -- canonicalization -----------------------------------------------------


def test_sampling_provenance_travels_with_every_item() -> None:
    """The enriched and boundary strata must never be pooled into a prevalence
    claim, which needs the stratum attached to each row."""
    adapter = _adapter(_standard([_thread("c1", "A comment.")]))
    result = adapter.discover(DiscoveryRequest(item_cap=50))

    items = [adapter.canonicalize(adapter.fetch(ref)) for ref in result.references]

    assert all(item.seed is not None for item in items)
    assert {item.seed.sampling_stratum for item in items if item.seed} == {
        SamplingStratum.boundary_control
    }
    assert all(item.seed.query_purpose for item in items if item.seed)


def test_a_comment_keeps_the_video_as_its_context() -> None:
    adapter = _adapter(_standard([_thread("c1", "A comment.")]))
    result = adapter.discover(DiscoveryRequest(item_cap=50))
    comment = next(
        reference
        for reference in result.references
        if reference.content_kind is ContentKind.social_comment
    )

    item = adapter.canonicalize(adapter.fetch(comment))

    assert item.context.root_text == "Panel discussion: reporting on faith communities"
    assert item.original_text == "A comment."


def test_no_author_identifier_is_retained() -> None:
    """`spec.md` section 18 forbids author search and identity resolution; the
    cheapest way to honour that is not to keep the identifier."""
    adapter = _adapter(_standard([_thread("c1", "A comment.")]))
    result = adapter.discover(DiscoveryRequest(item_cap=50))

    items = [adapter.canonicalize(adapter.fetch(ref)) for ref in result.references]

    for item in items:
        serialized = json.dumps(dict(item.provider_metadata))
        assert "authorChannelId" not in serialized
        assert "authorDisplayName" not in serialized


def test_a_malformed_provider_response_is_not_retried_forever() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        del request
        return httpx2.Response(200, content=b"not json")

    with pytest.raises(AdapterError) as raised:
        _adapter(handler).discover(DiscoveryRequest(item_cap=5))

    assert raised.value.is_retryable is False
