"""Contract for policy analysis and prepared platform reports (B-S18).

Nothing in this contract can express "submitted to the platform by Amanah",
because the product never does that. `status` distinguishes what the user
prepared from what the user says they filed, and `outcome` is what the user says
the platform did. `spec.md` FR-TOS-006 makes that separation mandatory, so it is
built into the vocabulary rather than left to a caller's discipline.

Every candidate is a *possible* match. The response carries the score, the tier,
the rule's official link, and its last-reviewed date so a reader judges the match
instead of inheriting it (FR-TOS-001, FR-TOS-002).
"""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import (
    ConfidenceTier,
    PreparedReportOutcome,
    PreparedReportStatus,
    ReportRecipientKind,
)
from amanah.reporting.prepared import MAXIMUM_DRAFT_LENGTH

#: Shown with every analysis. `spec.md` section 8.4 forbids claiming a violation
#: with certainty, so the disclosure travels with the candidates rather than
#: being left to the client to remember.
UNCERTAINTY_DISCLOSURE = (
    "These are possible policy matches, not findings. Read the platform's own rule "
    "and decide for yourself before preparing a report. Amanah never submits one."
)


class PolicyCandidateEntry(ResponseModel):
    """One catalogued rule that may apply to this item."""

    platform_policy_id: UUID
    platform: str
    policy_key: str
    title: str
    summary: str
    official_url: str = Field(description="The platform's own page for this rule.")
    version: str = Field(description="The catalogue snapshot a prepared report freezes.")
    last_reviewed_at: UtcDatetime | None
    recipient_kind: ReportRecipientKind
    official_report_url: str | None = Field(
        default=None, description="Where the *user* files it. Null when there is no form."
    )
    score: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    rationale: str


class PolicyAnalysisResponse(ResponseModel):
    """`POST /v1/items/{id}/policy-analysis` payload."""

    content_item_id: UUID
    candidates: list[PolicyCandidateEntry]
    matcher_version: str = Field(
        description="Which matcher produced these, so a stored match is attributable."
    )
    disclosure: str = Field(default=UNCERTAINTY_DISCLOSURE)
    meta: ResponseMeta


class PrepareReportRequest(RequestModel):
    """`POST /v1/prepared-reports` body.

    Both the policy and the version the user was shown are required. B-S18.3
    wants an explicit confirmation, and sending the identifier alone would let
    the catalogue move underneath the person between reading a rule and choosing
    it.
    """

    content_item_id: UUID
    platform_policy_id: UUID
    policy_version: str = Field(min_length=1, max_length=50)
    evidence_summary: str = Field(min_length=1, max_length=MAXIMUM_DRAFT_LENGTH)
    suggested_text: str = Field(min_length=1, max_length=MAXIMUM_DRAFT_LENGTH)
    draft_subject: str | None = Field(
        default=None,
        max_length=300,
        description=(
            "Subject of an email-style draft (FR-TOS-010). Required when the chosen "
            "policy has no official reporting form, forbidden when it does. The "
            "recipient is never accepted from a request: it comes from the catalogue."
        ),
    )


class RecordOutcomeRequest(RequestModel):
    """`PATCH /v1/prepared-reports/{id}` body."""

    status: PreparedReportStatus
    outcome: PreparedReportOutcome | None = None
    outcome_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _check_outcome(self) -> Self:
        if self.status is PreparedReportStatus.prepared:
            raise ValueError("a report cannot be moved back to prepared")
        if self.status is PreparedReportStatus.closed and self.outcome is None:
            raise ValueError("closing a report needs the outcome you saw")
        if self.status is PreparedReportStatus.submitted and self.outcome is not None:
            raise ValueError("record the outcome when you close the report, not when you file it")
        return self


class PreparedReportSummary(ResponseModel):
    """One report a user prepared, and what they later said happened."""

    id: UUID
    content_item_id: UUID
    platform: str
    platform_policy_id: UUID
    policy_version: str
    evidence_summary: str
    suggested_text: str
    status: PreparedReportStatus
    recipient_kind: ReportRecipientKind
    recipient_address: str | None = Field(
        default=None,
        description="Allow-listed address of an email-style draft. Nothing is ever sent to it.",
    )
    draft_subject: str | None = None
    submitted_at: UtcDatetime | None = Field(
        default=None, description="When the user said they filed it. Never a platform receipt."
    )
    outcome: PreparedReportOutcome | None = None
    outcome_note: str | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class PreparedReportResponse(ResponseModel):
    """`POST /v1/prepared-reports` and `PATCH /v1/prepared-reports/{id}` payload."""

    report: PreparedReportSummary
    meta: ResponseMeta
