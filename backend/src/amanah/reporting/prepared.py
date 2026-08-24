"""Preparing a platform report, and recording what the user says happened (B-S18.3 to B-S18.8).

The hard boundary is the first thing to state: nothing in this module makes an
outbound request. There is no reporting-API client, no mail transport, and no URL
taken from a caller. `spec.md` FR-TOS-006 forbids submitting a report or claiming
a platform received one, and FR-TOS-010 keeps the email variant a *draft* — the
only address it can carry is one a reviewer put in the catalogue.

`submitted_at` is when the *user told us* they filed it. Nothing anywhere records
a platform acknowledgement, because the product never receives one.

The policy version is confirmed rather than looked up. B-S18.3 requires the user
to pick a rule and B-S18.5's history has to stay honest, so the request names both
the policy and the version it was shown, and a catalogue that has moved on since
is a conflict the user has to see rather than a silent substitution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from amanah.contributions.rate_limit import PREPARED_REPORT_LIMIT, enforce
from amanah.contributions.timeline import ContributionTimeline
from amanah.db.models.content import ContentItem
from amanah.db.models.reporting import PlatformPolicy, PreparedPlatformReport
from amanah.domain.enums import (
    ContributionEventType,
    ContributionType,
    PreparedReportOutcome,
    PreparedReportStatus,
    PublicationStatus,
    ReportRecipientKind,
)

logger = logging.getLogger(__name__)

#: Longest evidence summary and suggested wording accepted. A report body is a
#: paragraph or two; a longer one is either pasted source text or an attempt to
#: use the field as storage.
MAXIMUM_DRAFT_LENGTH = 4000

_PREPARED_MESSAGE = "You prepared a report for this item. Submit it on the platform yourself."
_SUBMITTED_MESSAGE = "You recorded that you submitted this report."
_CLOSED_MESSAGE = "You recorded the outcome of this report."

#: The only transitions a prepared report may make. `prepared` is where every
#: record starts; a platform outcome can only follow the user saying they filed
#: it. There is no transition into `prepared` from anywhere, because that would
#: mean un-submitting something.
_ALLOWED_TRANSITIONS: dict[PreparedReportStatus, frozenset[PreparedReportStatus]] = {
    PreparedReportStatus.prepared: frozenset({PreparedReportStatus.submitted}),
    PreparedReportStatus.submitted: frozenset({PreparedReportStatus.closed}),
    PreparedReportStatus.closed: frozenset(),
}


class PreparationRejectedError(ValueError):
    """The report cannot be prepared or updated as asked."""

    def __init__(self, message: str, *, is_conflict: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.is_conflict = is_conflict


@dataclass(frozen=True, slots=True)
class PreparationRequest:
    """A user's confirmed intent to prepare one report.

    `platform_policy_id` and `policy_version` together are the confirmation
    B-S18.3 requires. Sending the identifier alone would let the catalogue move
    underneath the person between reading a rule and choosing it.
    """

    content_item_id: UUID
    platform_policy_id: UUID
    policy_version: str
    evidence_summary: str
    suggested_text: str
    draft_subject: str | None = None


@dataclass(frozen=True, slots=True)
class OutcomeUpdate:
    """What the user says has happened since they prepared it."""

    status: PreparedReportStatus
    outcome: PreparedReportOutcome | None = None
    outcome_note: str | None = None


class PreparedReportService:
    """Owns every transition of `prepared_platform_reports`."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._timeline = ContributionTimeline(session)

    def prepare(self, *, user_id: UUID, request: PreparationRequest) -> PreparedPlatformReport:
        """Store one prepared report against a confirmed policy version."""
        policy = self._session.get(PlatformPolicy, request.platform_policy_id)
        if policy is None or policy.status is not PublicationStatus.published:
            raise PreparationRejectedError("That policy is not in the reviewed catalogue.")
        if policy.version != request.policy_version:
            # B-S18.8: a stale version is shown to the user rather than quietly
            # swapped, because the wording they wrote was about the old rule.
            raise PreparationRejectedError(
                "This policy has been re-reviewed since you saw it. Check the rule again.",
                is_conflict=True,
            )
        if self._session.get(ContentItem, request.content_item_id) is None:
            raise PreparationRejectedError("That item was not found.")

        existing = self._find_existing(
            user_id=user_id,
            content_item_id=request.content_item_id,
            platform=policy.platform,
        )
        if existing is not None:
            # FR-TOS-009: one prepared report per person, item, and platform.
            # Preparing the same one twice is the shape mass reporting takes.
            raise PreparationRejectedError(
                "You have already prepared a report for this item on this platform.",
                is_conflict=True,
            )

        enforce(
            self._session,
            PREPARED_REPORT_LIMIT,
            user_id=user_id,
            owner_column=PreparedPlatformReport.user_id,
            created_column=PreparedPlatformReport.created_at,
        )

        is_email_draft = policy.recipient_kind is ReportRecipientKind.allowlist_email
        if is_email_draft and not request.draft_subject:
            raise PreparationRejectedError("An email-style draft needs a subject line.")
        if not is_email_draft and request.draft_subject:
            raise PreparationRejectedError(
                "This platform has a reporting form, so the draft carries no subject."
            )

        report = PreparedPlatformReport(
            user_id=user_id,
            content_item_id=request.content_item_id,
            platform=policy.platform,
            platform_policy_id=policy.id,
            policy_version=policy.version,
            evidence_summary=request.evidence_summary,
            suggested_text=request.suggested_text,
            status=PreparedReportStatus.prepared,
            recipient_kind=policy.recipient_kind,
            # The address comes from the reviewed catalogue and never from the
            # request. A caller-supplied recipient would make this a mail relay.
            recipient_address=policy.report_email if is_email_draft else None,
            draft_subject=request.draft_subject if is_email_draft else None,
        )
        self._session.add(report)
        self._session.flush()
        self._timeline.append(
            user_id=user_id,
            contribution_type=ContributionType.prepared_platform_report,
            contribution_id=report.id,
            event_type=ContributionEventType.created,
            public_message=_PREPARED_MESSAGE,
        )
        self._session.commit()
        logger.info(
            "platform report prepared",
            extra={
                "prepared_report_id": str(report.id),
                "platform": policy.platform,
                "recipient_kind": policy.recipient_kind.value,
            },
        )
        return report

    def record_outcome(
        self, report_id: UUID, *, user_id: UUID, update: OutcomeUpdate
    ) -> PreparedPlatformReport:
        """Record that the user submitted it, or what the platform did.

        Ownership is checked here as well as at the route: this is the only place
        that writes the row, so the check belongs where it cannot be routed past.
        """
        report = self._session.get(PreparedPlatformReport, report_id)
        if report is None or report.user_id != user_id:
            raise PreparationRejectedError("That prepared report was not found.")
        if update.status not in _ALLOWED_TRANSITIONS[report.status]:
            raise PreparationRejectedError(
                f"A {report.status.value} report cannot become {update.status.value}.",
                is_conflict=True,
            )
        if update.status is PreparedReportStatus.closed and update.outcome is None:
            raise PreparationRejectedError("Closing a report needs the outcome you saw.")

        report.status = update.status
        if update.status is PreparedReportStatus.submitted:
            # What the user told us. Never a platform acknowledgement: the
            # product has no channel that could receive one.
            report.submitted_at = datetime.now(UTC)
        if update.outcome is not None:
            report.outcome = update.outcome
            report.outcome_note = update.outcome_note

        message = (
            _SUBMITTED_MESSAGE
            if update.status is PreparedReportStatus.submitted
            else _CLOSED_MESSAGE
        )
        self._timeline.append(
            user_id=user_id,
            contribution_type=ContributionType.prepared_platform_report,
            contribution_id=report.id,
            event_type=ContributionEventType.status_changed,
            public_message=message,
        )
        self._session.commit()
        logger.info(
            "prepared report updated",
            extra={
                "prepared_report_id": str(report.id),
                "status": update.status.value,
                "outcome": update.outcome.value if update.outcome else None,
            },
        )
        return report

    def _find_existing(
        self, *, user_id: UUID, content_item_id: UUID, platform: str
    ) -> PreparedPlatformReport | None:
        return self._session.execute(
            select(PreparedPlatformReport).where(
                PreparedPlatformReport.user_id == user_id,
                PreparedPlatformReport.content_item_id == content_item_id,
                PreparedPlatformReport.platform == platform,
            )
        ).scalar_one_or_none()
