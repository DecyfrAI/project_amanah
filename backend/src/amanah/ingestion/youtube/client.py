"""The official YouTube Data API v3 boundary (B-S10.3, B-S10.7).

Three endpoints, and only three: `search.list` for query discovery,
`videos.list` for metadata, and `commentThreads.list` for top-level comments and
their bounded replies. There is no scraping path, no transcript retrieval, and
no fallback to the watch page — `AGENTS.md` and `spec.md` section 10.2 both
prohibit collecting from a platform outside its official access, and a fallback
that quietly did so would be the whole prohibition undone.

Quota is treated as a first-class outcome rather than an error. When the API says
the day's quota is spent, the run **defers**: it stops, keeps its checkpoint, and
reports a coverage gap. `spec.md` section 17.2 requires exactly that, because a
quota-truncated collection presented as a complete one is an undercount that
reads as a decline.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx2

from amanah.ingestion.contract import AdapterError
from amanah.ingestion.http import HttpLimits, raise_for_status, read_bounded

logger = logging.getLogger(__name__)

API_BASE_URL = "https://www.googleapis.com/youtube/v3"

#: The provider's own maximum for these endpoints. Asking for more is an error,
#: so this is a ceiling rather than a preference.
MAXIMUM_PAGE_SIZE = 50

#: Reasons the provider gives for a `403` that mean "come back later" rather than
#: "you may not do this". They are the difference between a deferral and a policy
#: block, so they are matched explicitly instead of by guessing from the status.
QUOTA_REASONS = frozenset({"quotaExceeded", "rateLimitExceeded", "userRateLimitExceeded"})

#: Reasons that mean the *item* is unavailable, not the connector. A video whose
#: comments are disabled is a coverage gap on that video alone.
COMMENTS_DISABLED_REASONS = frozenset({"commentsDisabled"})


class QuotaDeferredError(AdapterError):
    """The provider's quota is spent. Checkpoint, stop, and report the gap."""

    def __init__(self) -> None:
        super().__init__("quota_deferred", is_retryable=True)


class CommentsDisabledError(AdapterError):
    """The video exists but has comments turned off."""

    def __init__(self) -> None:
        super().__init__("comments_disabled", is_retryable=False)


@dataclass(frozen=True, slots=True)
class ApiPage:
    """One page of results and the token that continues it."""

    items: tuple[Mapping[str, Any], ...]
    next_page_token: str | None


class YouTubeClient:
    """A thin, bounded wrapper over the three endpoints this product uses."""

    def __init__(self, *, api_key: str, client: httpx2.Client, limits: HttpLimits) -> None:
        self._api_key = api_key
        self._client = client
        self._limits = limits

    def search_videos(
        self,
        *,
        query: str,
        published_after: str | None,
        published_before: str | None,
        page_size: int,
        page_token: str | None = None,
        relevance_language: str = "en",
    ) -> ApiPage:
        """Find videos matching one approved query inside an explicit window."""
        parameters: dict[str, str] = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": str(min(page_size, MAXIMUM_PAGE_SIZE)),
            "relevanceLanguage": relevance_language,
            "order": "date",
        }
        if published_after:
            parameters["publishedAfter"] = published_after
        if published_before:
            parameters["publishedBefore"] = published_before
        if page_token:
            parameters["pageToken"] = page_token
        return self._get("search", parameters)

    def list_videos(self, video_ids: tuple[str, ...]) -> ApiPage:
        """Retrieve metadata for up to one page of videos."""
        if not video_ids:
            return ApiPage(items=(), next_page_token=None)
        return self._get(
            "videos",
            {
                "part": "snippet",
                "id": ",".join(video_ids[:MAXIMUM_PAGE_SIZE]),
                "maxResults": str(MAXIMUM_PAGE_SIZE),
            },
        )

    def list_comment_threads(
        self, *, video_id: str, page_size: int, page_token: str | None = None
    ) -> ApiPage:
        """Retrieve top-level comments and the replies the API returns with them."""
        parameters: dict[str, str] = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": str(min(page_size, MAXIMUM_PAGE_SIZE)),
            "order": "time",
            "textFormat": "plainText",
        }
        if page_token:
            parameters["pageToken"] = page_token
        return self._get("commentThreads", parameters)

    def _get(self, resource: str, parameters: Mapping[str, str]) -> ApiPage:
        query = urlencode({**parameters, "key": self._api_key})
        response = read_bounded(
            self._client, f"{API_BASE_URL}/{resource}?{query}", limits=self._limits
        )
        if response.status_code == 403:
            self._raise_for_forbidden(response.content)
        raise_for_status(response)

        try:
            document = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise AdapterError("provider_response_malformed", is_retryable=False) from exc
        if not isinstance(document, dict):
            raise AdapterError("provider_response_malformed", is_retryable=False)

        items = document.get("items") or []
        return ApiPage(
            items=tuple(item for item in items if isinstance(item, dict)),
            next_page_token=document.get("nextPageToken"),
        )

    def _raise_for_forbidden(self, body: bytes) -> None:
        """Separate "quota spent" from "not permitted" using the stated reason.

        The reason string is the provider's, so it is matched against a known set
        and never echoed onward: an unrecognised one falls through to the generic
        access-required path rather than being reported verbatim.
        """
        reasons = _error_reasons(body)
        if reasons & QUOTA_REASONS:
            logger.warning("youtube quota deferred")
            raise QuotaDeferredError
        if reasons & COMMENTS_DISABLED_REASONS:
            raise CommentsDisabledError
        raise AdapterError("provider_access_required", is_policy_block=True)


def _error_reasons(body: bytes) -> frozenset[str]:
    try:
        document = json.loads(body)
    except json.JSONDecodeError:
        return frozenset()
    errors = document.get("error", {}).get("errors", []) if isinstance(document, dict) else []
    return frozenset(str(error.get("reason", "")) for error in errors if isinstance(error, dict))
