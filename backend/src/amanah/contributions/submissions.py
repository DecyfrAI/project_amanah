"""User URL submissions and their lifecycle (B-S16).

`spec.md` FR-SUBMIT-005 requires a valid submission to return `processing`
immediately, and FR-SUBMIT-006 requires the work itself to go through the same
pipeline as collected content. Those two together decide the shape here: the
request writes a `content_submissions` row and dispatches a `collection_runs`
row for the `user_submission` source, and then returns. No network call happens
inside the request, which is also what keeps the safe-retrieval path off the
critical path of an API response.

Idempotency is natural rather than header-based (`rules/api.md` section 12.3):
the partial unique index on `(user_id, canonical_url)` is the constraint, so the
same person resubmitting the same address links to the record they already have
instead of starting a second run. `canonical_url` here is the normalized form of
what the user typed; the *resolved* address after redirects belongs to the
content item the submission eventually points at, and the two are deliberately
not the same field.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from amanah.canonical.store import StoredItem
from amanah.canonical.urls import canonical_url_key
from amanah.contributions.rate_limit import SUBMISSION_LIMIT, enforce
from amanah.contributions.timeline import ContributionTimeline
from amanah.db.models.community import ContentSubmission
from amanah.db.models.content import ContentItem
from amanah.domain.enums import (
    CollectionMode,
    ContributionEventType,
    ContributionType,
    SubmissionStatus,
)
from amanah.ingestion.urls.safe_fetch import validate_syntax
from amanah.jobs.runs import CollectionRunService, RunDispatch
from amanah.observability.metrics import MetricName, record_metric

logger = logging.getLogger(__name__)

#: Configured key of the source every user submission is attributed to.
USER_SUBMISSION_SOURCE_KEY = "user_submission"

#: One URL per request (`spec.md` FR-SUBMIT-002), so a run started for a
#: submission collects exactly that one item.
SUBMISSION_ITEM_CAP = 1

#: Adapter version stamped on the dispatched run. The worker replaces it with
#: the version that actually ran, so a dispatch never claims a capability the
#: deployed code does not have.
DISPATCH_ADAPTER_VERSION = "pending"

#: The lines a user sees on their timeline. Composed from controlled vocabulary
#: here so no provider text, reviewer note, or source wording can reach one.
_STATUS_MESSAGES: dict[SubmissionStatus, str] = {
    SubmissionStatus.processing: "We received this link and queued it for analysis.",
    SubmissionStatus.analyzed: "We analysed this link. Open the item to see the result.",
    SubmissionStatus.duplicate: "We already had this link. Your submission points at that item.",
    SubmissionStatus.unsupported: "We cannot analyse this kind of page yet.",
    SubmissionStatus.inaccessible: "We could not read this page. It may be private or removed.",
    SubmissionStatus.rejected: "This address is not one we are able to retrieve.",
    SubmissionStatus.failed: "Something went wrong analysing this link. You can submit it again.",
}


class SubmissionRejectedError(ValueError):
    """The submitted address is not a public HTTP(S) URL.

    Raised before anything is written, and before any name is resolved: an
    unusable address is a client error, not a submission with a sad outcome.
    """

    def __init__(self, safe_error_code: str) -> None:
        super().__init__(safe_error_code)
        self.safe_error_code = safe_error_code


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    """One submission and whether this request is what created it."""

    submission: ContentSubmission
    is_new: bool


class SubmissionService:
    """Owns every transition of `content_submissions`."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._timeline = ContributionTimeline(session)

    def submit(self, *, user_id: UUID, submitted_url: str) -> SubmissionResult:
        """Record a submission and queue the work, or return the existing one.

        Order matters. The row is written and committed as `processing` before
        the run is dispatched, so a dispatch that fails leaves a submission the
        user can see and retry rather than a silent nothing.
        """
        # The resolver-free half of the fetcher's own check, so an address that
        # can never be retrieved — a private literal, an unsafe port, credentials
        # in the URL — is a `422` the person sees now rather than a row that sits
        # at `processing` until a worker refuses it. Name resolution deliberately
        # stays out of the request path: a host that is momentarily unresolvable
        # is an `inaccessible` outcome, not an invalid address. `SafeUrlFetcher`
        # re-validates every hop with DNS, and that is the security boundary.
        checked = validate_syntax(submitted_url)
        if isinstance(checked, tuple):
            _status, code = checked
            raise SubmissionRejectedError(code)
        normalized = checked

        existing = self._find_own_submission(user_id=user_id, canonical_url=normalized)
        if existing is not None:
            logger.info(
                "submission absorbed a duplicate delivery",
                extra={"submission_id": str(existing.id), "status": existing.status.value},
            )
            return SubmissionResult(submission=existing, is_new=False)

        enforce(
            self._session,
            SUBMISSION_LIMIT,
            user_id=user_id,
            owner_column=ContentSubmission.user_id,
            created_column=ContentSubmission.submitted_at,
        )

        known_item_id = self._find_existing_item(normalized)
        status = (
            SubmissionStatus.duplicate if known_item_id is not None else SubmissionStatus.processing
        )
        submission = ContentSubmission(
            user_id=user_id,
            submitted_url=submitted_url,
            canonical_url=normalized,
            content_item_id=known_item_id,
            status=status,
        )
        self._session.add(submission)
        self._session.flush()
        self._timeline.append(
            user_id=user_id,
            contribution_type=ContributionType.url_submission,
            contribution_id=submission.id,
            event_type=ContributionEventType.created,
            public_message=_STATUS_MESSAGES[status],
        )
        self._session.commit()
        logger.info(
            "submission recorded",
            extra={"submission_id": str(submission.id), "status": status.value},
        )
        record_metric(MetricName.contributions, action="submission", outcome=status.value)

        if status is SubmissionStatus.processing:
            self._enqueue(submission)
        return SubmissionResult(submission=submission, is_new=True)

    def settle(
        self,
        submission_id: UUID,
        *,
        status: SubmissionStatus,
        safe_error_code: str | None = None,
    ) -> None:
        """Record a terminal outcome that produced no content item.

        Used for the states where retrieval finished but there is nothing to
        analyse: unsupported, inaccessible, rejected, failed. Each one is a
        result the user is shown, not an error the service swallows.
        """
        submission = self._session.get(ContentSubmission, submission_id)
        if submission is None:
            logger.warning("settlement skipped: no such submission")
            return
        submission.status = status
        submission.safe_error_code = safe_error_code
        submission.processed_at = _now()
        self._timeline.append(
            user_id=submission.user_id,
            contribution_type=ContributionType.url_submission,
            contribution_id=submission.id,
            event_type=ContributionEventType.status_changed,
            public_message=_STATUS_MESSAGES[status],
        )
        self._session.commit()
        logger.info(
            "submission settled",
            extra={
                "submission_id": str(submission.id),
                "status": status.value,
                "safe_error_code": safe_error_code,
            },
        )

    def link_stored_item(self, submission_id: UUID, stored: StoredItem) -> None:
        """Attach the canonical item the pipeline produced (FR-SUBMIT-008).

        A stored item that turned out to duplicate an existing row gives the
        submission `duplicate` rather than `analyzed`: the user still reaches an
        item, and the history does not claim we analysed something twice.
        """
        submission = self._session.get(ContentSubmission, submission_id)
        if submission is None:
            logger.warning("link skipped: no such submission")
            return
        status = SubmissionStatus.duplicate if stored.is_duplicate else SubmissionStatus.analyzed
        submission.content_item_id = stored.content_item_id
        submission.status = status
        submission.safe_error_code = None
        submission.processed_at = _now()
        self._timeline.append(
            user_id=submission.user_id,
            contribution_type=ContributionType.url_submission,
            contribution_id=submission.id,
            event_type=ContributionEventType.status_changed,
            public_message=_STATUS_MESSAGES[status],
        )
        self._session.commit()
        logger.info(
            "submission linked to a content item",
            extra={
                "submission_id": str(submission.id),
                "content_item_id": str(stored.content_item_id),
                "status": status.value,
            },
        )

    def list_pending(self, *, limit: int) -> tuple[ContentSubmission, ...]:
        """Submissions still waiting for retrieval, oldest first.

        The user-submission adapter's discovery reads this: the queue of things
        people asked for *is* what that source discovers.
        """
        statement = (
            select(ContentSubmission)
            .where(ContentSubmission.status == SubmissionStatus.processing)
            .order_by(ContentSubmission.submitted_at.asc(), ContentSubmission.id.asc())
            .limit(limit)
        )
        return tuple(self._session.execute(statement).scalars().all())

    def _find_own_submission(
        self, *, user_id: UUID, canonical_url: str
    ) -> ContentSubmission | None:
        return self._session.execute(
            select(ContentSubmission).where(
                ContentSubmission.user_id == user_id,
                ContentSubmission.canonical_url == canonical_url,
            )
        ).scalar_one_or_none()

    def _find_existing_item(self, canonical_url: str) -> UUID | None:
        """The item this URL already produced, whoever submitted it first.

        FR-SUBMIT-004: a canonical duplicate links to the existing item rather
        than being retrieved and classified a second time.
        """
        return self._session.execute(
            select(ContentItem.id).where(
                ContentItem.canonical_url_key == canonical_url_key(canonical_url)
            )
        ).scalar_one_or_none()

    def _enqueue(self, submission: ContentSubmission) -> None:
        """Queue the canonical pipeline for one submission.

        The idempotency key is the submission, which is the work — not the
        delivery — so a retried request that reached the same submission cannot
        produce a second run.
        """
        CollectionRunService(self._session).dispatch(
            RunDispatch(
                source_key=USER_SUBMISSION_SOURCE_KEY,
                mode=CollectionMode.manual,
                adapter_version=DISPATCH_ADAPTER_VERSION,
                idempotency_key=f"submission:{submission.id}",
                item_cap=SUBMISSION_ITEM_CAP,
                requested_by=submission.user_id,
            )
        )
        logger.info(
            "submission queued for collection",
            extra={"submission_id": str(submission.id)},
        )


def _now() -> datetime:
    return datetime.now(UTC)
