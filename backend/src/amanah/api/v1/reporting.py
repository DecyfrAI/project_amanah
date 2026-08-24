"""`/v1/items/{id}/policy-analysis` and `/v1/prepared-reports` (B-S18).

No route here makes an outbound request. Analysis reads the reviewed catalogue
and the stored prediction; preparation writes a record. `spec.md` FR-TOS-006
forbids submitting a report or claiming a platform received one, and the absence
of any client in this module is what makes that structural rather than a promise.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from amanah.api.dependencies import (
    CurrentUser,
    DatabaseSession,
    build_response_meta,
    get_settings,
)
from amanah.api.errors import ApiError, ConflictError, ResourceNotFoundError
from amanah.api.schemas.errors import ErrorCode
from amanah.api.schemas.reporting import (
    PolicyAnalysisResponse,
    PolicyCandidateEntry,
    PreparedReportResponse,
    PrepareReportRequest,
    RecordOutcomeRequest,
)
from amanah.api.v1.mappers import to_prepared_report
from amanah.db.repositories.contributions import ContributionRepository
from amanah.db.views import authenticated_items
from amanah.domain.enums import HateType, Stance
from amanah.reporting.policies import CataloguePolicyMatcher, PolicyCandidate
from amanah.reporting.prepared import (
    OutcomeUpdate,
    PreparationRejectedError,
    PreparationRequest,
    PreparedReportService,
)
from amanah.settings import Settings

router = APIRouter(tags=["reporting"])


@router.post(
    "/items/{content_item_id}/policy-analysis",
    summary="List possible platform-policy matches for one item",
)
def analyse_policies(
    content_item_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PolicyAnalysisResponse:
    """Return the reviewed rules that may apply, strongest first.

    Read through the authenticated item projection, so an item the caller cannot
    see produces `404` rather than a candidate list. An item the classifier did
    not read as anti-Muslim produces an empty list: offering a rule for
    counterspeech, a quotation, or neutral reporting would turn this into a way
    to report people for discussing the subject.
    """
    row = session.execute(
        select(authenticated_items).where(authenticated_items.c.id == content_item_id)
    ).one_or_none()
    if row is None:
        raise ResourceNotFoundError("This item was not found.")
    if row.prediction_id is None:
        raise ApiError(
            code=ErrorCode.validation_failed,
            status_code=422,
            message="This item has not been classified yet.",
        )

    matcher = CataloguePolicyMatcher(session)
    candidates = matcher.candidates(
        platform=row.platform,
        hate_types=tuple(HateType(kind) for kind in row.hate_types or ()),
        severity=row.severity or 0,
        stance=Stance(row.stance),
    )
    return PolicyAnalysisResponse(
        content_item_id=content_item_id,
        candidates=[_to_candidate(candidate) for candidate in candidates],
        matcher_version=matcher.matcher_version,
        meta=build_response_meta(settings),
    )


@router.post(
    "/prepared-reports",
    summary="Save a prepared platform report",
    status_code=status.HTTP_201_CREATED,
)
def prepare_report(
    request: PrepareReportRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PreparedReportResponse:
    """Store the wording the user prepared against the rule they confirmed.

    The rule and the version the user was shown both have to be sent: B-S18.3
    wants an explicit confirmation, and a catalogue that has moved on since is
    reported as a conflict rather than silently substituted.
    """
    service = PreparedReportService(session)
    try:
        report = service.prepare(
            user_id=user.user_id,
            request=PreparationRequest(
                content_item_id=request.content_item_id,
                platform_policy_id=request.platform_policy_id,
                policy_version=request.policy_version,
                evidence_summary=request.evidence_summary,
                suggested_text=request.suggested_text,
                draft_subject=request.draft_subject,
            ),
        )
    except PreparationRejectedError as exc:
        raise _rejection(exc) from exc

    return _report_response(session, report.id, settings)


@router.patch(
    "/prepared-reports/{report_id}",
    summary="Record that you submitted a prepared report, or what happened to it",
)
def record_outcome(
    report_id: UUID,
    request: RecordOutcomeRequest,
    user: CurrentUser,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PreparedReportResponse:
    """Record the user's own account of what they did and what followed.

    `submitted_at` is when the *user said* they filed it. Nothing here is a
    platform acknowledgement, because the product has no channel that receives
    one.
    """
    try:
        PreparedReportService(session).record_outcome(
            report_id,
            user_id=user.user_id,
            update=OutcomeUpdate(
                status=request.status,
                outcome=request.outcome,
                outcome_note=request.outcome_note,
            ),
        )
    except PreparationRejectedError as exc:
        raise _rejection(exc) from exc

    return _report_response(session, report_id, settings)


def _report_response(
    session: DatabaseSession, report_id: UUID, settings: Settings
) -> PreparedReportResponse:
    row = ContributionRepository(session).get_prepared_report(report_id)
    if row is None:
        raise ResourceNotFoundError("This prepared report was not found.")
    return PreparedReportResponse(
        report=to_prepared_report(row), meta=build_response_meta(settings)
    )


def _rejection(exc: PreparationRejectedError) -> ApiError:
    """Map a refusal onto a status a client can act on."""
    if exc.is_conflict:
        return ConflictError(exc.message)
    return ApiError(
        code=ErrorCode.validation_failed,
        status_code=422,
        message=exc.message,
    )


def _to_candidate(candidate: PolicyCandidate) -> PolicyCandidateEntry:
    return PolicyCandidateEntry(
        platform_policy_id=candidate.platform_policy_id,
        platform=candidate.platform,
        policy_key=candidate.policy_key,
        title=candidate.title,
        summary=candidate.summary,
        official_url=candidate.official_url,
        version=candidate.version,
        last_reviewed_at=candidate.last_reviewed_at,
        recipient_kind=candidate.recipient_kind,
        official_report_url=candidate.official_report_url,
        score=candidate.score,
        confidence_tier=candidate.confidence_tier,
        rationale=candidate.rationale,
    )
