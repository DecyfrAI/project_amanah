"""The adapter that turns a user's submitted URL into canonical content (B-S16.3).

This source's "provider" is two things: the queue of submissions people have made,
and the public web page each one points at. Discovery reads the queue; retrieval
goes through `SafeUrlFetcher`, which is the only code in this service permitted
to fetch an address a user chose.

Retrieval happens during `discover` rather than in `fetch`, which is the same
shape the news and YouTube adapters use and for the same reason: the outcome of
one HTTP request decides both whether there is anything to canonicalize *and*
what the submission's terminal state is. Doing it in two stages would mean either
requesting the page twice or checkpointing a page body into the job queue, and
neither is something this product should do to somebody's URL.

A submission that cannot be retrieved is settled here, not raised. `spec.md`
FR-SUBMIT-007 makes `unsupported`, `inaccessible`, `rejected`, and `failed`
outcomes the user is shown; treating them as adapter failures would dead-letter a
job over a paywall and leave the person staring at "processing" forever.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from amanah.contributions.submissions import (
    USER_SUBMISSION_SOURCE_KEY,
    SubmissionService,
)
from amanah.domain.enums import ContentKind
from amanah.ingestion.contract import (
    AdapterError,
    BaseSourceAdapter,
    CanonicalContentItem,
    ContentContext,
    DiscoveryRequest,
    DiscoveryResult,
    FetchedPayload,
    SourceReference,
)
from amanah.ingestion.urls.safe_fetch import RetrievalResult, SafeUrlFetcher
from amanah.settings import Settings

logger = logging.getLogger(__name__)

ADAPTER_VERSION = "user-submission-1.0.0"

#: Key the canonical item carries so the pipeline can link the stored row back to
#: the submission that asked for it. It lives in `provider_metadata`, which is
#: the opaque per-source column no projection has a column for — a submission
#: identifier is this source's own bookkeeping and not something a reader needs.
SUBMISSION_ID_KEY = "content_submission_id"


class UserSubmissionAdapter(BaseSourceAdapter):
    """Serves canonical items from the queue of user-submitted URLs."""

    def __init__(self, session: Session, *, settings: Settings) -> None:
        super().__init__(
            source_key=USER_SUBMISSION_SOURCE_KEY,
            adapter_version=ADAPTER_VERSION,
            is_fixture=False,
        )
        self._session = session
        self._submissions = SubmissionService(session)
        self._fetcher = SafeUrlFetcher(settings)

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Retrieve each pending submission and keep the ones with a page.

        The window on the request is ignored on purpose: a submission is work a
        person asked for, and deferring it because its row falls outside a
        collection window would strand it.
        """
        pending = self._submissions.list_pending(limit=max(request.item_cap, 1))
        references: list[SourceReference] = []
        warnings: list[str] = []
        counts = {"pending": len(pending), "retrieved": 0, "unavailable": 0}

        for submission in pending:
            url = submission.canonical_url or submission.submitted_url
            result = self._fetcher.retrieve(url)
            if not result.is_analyzed:
                self._submissions.settle(
                    submission.id,
                    status=result.status,
                    safe_error_code=result.safe_error_code,
                )
                counts["unavailable"] += 1
                warnings.append(
                    "One submitted link could not be read and is recorded as "
                    f"{result.status.value}."
                )
                continue

            counts["retrieved"] += 1
            references.append(
                SourceReference(
                    reference_id=str(submission.id),
                    content_kind=ContentKind.news_article,
                    hint=_reference_hint(submission.id, submission.user_id, result),
                )
            )

        return DiscoveryResult(
            references=tuple(references),
            cursor=None,
            coverage_warnings=tuple(dict.fromkeys(warnings)),
            counts=counts,
        )

    def fetch(self, reference: SourceReference) -> FetchedPayload:
        """Hand back what discovery already retrieved.

        No second request. The page was read once, under one set of redirect and
        byte limits, and reading it again would double the load this product puts
        on somebody else's server for one person's link.
        """
        if not reference.hint:
            raise AdapterError("submission_reference_incomplete")
        return FetchedPayload(
            reference=reference,
            payload=dict(reference.hint),
            retrieved_at=_parse_time(reference.hint.get("retrieved_at")),
        )

    def canonicalize(self, payload: FetchedPayload) -> CanonicalContentItem:
        """Translate one retrieved page into the canonical shape.

        Metadata only. `spec.md` section 10.5 permits a headline, a publisher, a
        short excerpt, and a link back; taking the article body would be
        republication performed on request.
        """
        values = payload.payload
        canonical_url = str(values["canonical_url"])
        title = _optional(values.get("title"))
        return CanonicalContentItem(
            source_key=USER_SUBMISSION_SOURCE_KEY,
            # Namespaced on the submission, so re-running the stage converges on
            # the same row and two people submitting the same link still produce
            # one item through canonical-URL deduplication.
            source_item_id=f"submission:{values[SUBMISSION_ID_KEY]}",
            content_kind=ContentKind.news_article,
            observed_at=payload.retrieved_at,
            is_fixture=False,
            canonical_url=canonical_url,
            title=title,
            permitted_excerpt=_optional(values.get("description")),
            publisher_or_container=_optional(values.get("site_name")),
            language=_optional(values.get("language")),
            context=ContentContext(title=title),
            provider_metadata={
                SUBMISSION_ID_KEY: str(values[SUBMISSION_ID_KEY]),
            },
            submitted_origin=UUID(str(values["user_id"])),
        )


def build_user_submission_adapter(session: Session, settings: Settings) -> UserSubmissionAdapter:
    """Construct the adapter for one worker session."""
    return UserSubmissionAdapter(session, settings=settings)


def submission_id_from(item: CanonicalContentItem) -> UUID | None:
    """The submission a canonical item came from, if it came from one.

    Returns `None` for everything collected rather than submitted, which is what
    lets the pipeline call this unconditionally.
    """
    raw = item.provider_metadata.get(SUBMISSION_ID_KEY)
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        logger.warning("canonical item carried an unreadable submission identifier")
        return None


def _reference_hint(submission_id: UUID, user_id: UUID, result: RetrievalResult) -> dict[str, Any]:
    """Everything canonicalization needs, and nothing the page body contained."""
    metadata = result.metadata
    if metadata is None:  # pragma: no cover - only an analyzed result reaches here
        raise AdapterError("submission_metadata_missing")
    retrieved_at = result.retrieved_at or datetime.now(UTC)
    return {
        SUBMISSION_ID_KEY: str(submission_id),
        "user_id": str(user_id),
        "canonical_url": metadata.canonical_url or result.canonical_url,
        "title": metadata.title,
        "description": metadata.description,
        "site_name": metadata.site_name,
        "language": metadata.language,
        "retrieved_at": retrieved_at.isoformat(),
    }


def _parse_time(raw: object) -> datetime:
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    return datetime.now(UTC)


def _optional(value: object) -> str | None:
    """Keep an absent field absent rather than turning it into an empty string."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
