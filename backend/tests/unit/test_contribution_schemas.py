"""Boundary validation on the Milestone 5 request models (B-S16, B-S17, B-S18, B-S27).

These are the checks that run before anything reaches a service, so what they
prove is that a malformed or over-reaching request is refused at the edge rather
than part-way through a write.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from amanah.api.schemas.contributions import OpenDisputeRequest, SubmitUrlRequest
from amanah.api.schemas.discussion import (
    CreateCaptureRequest,
    CreateInsightRequest,
    CreatePostRequest,
    InsightSummary,
    UpdateProfileRequest,
)
from amanah.api.schemas.reporting import PrepareReportRequest, RecordOutcomeRequest
from amanah.api.schemas.review import AppendDecisionRequest
from amanah.domain.enums import (
    OnboardingStatus,
    PreparedReportOutcome,
    PreparedReportStatus,
    ReviewDecision,
)

WINDOW_START = datetime(2026, 6, 1, tzinfo=UTC)
WINDOW_END = datetime(2026, 6, 30, tzinfo=UTC)
FILTER_HASH = "a1b2c3d4e5f60718"


def _insight(**overrides: object) -> CreateInsightRequest:
    values: dict[str, object] = {
        "title": "Rate in the monitored sample",
        "claim": "12 of 400 monitored items were classified likely anti-Muslim.",
        "metric": "likely_anti_muslim_rate",
        "numerator": 12,
        "denominator": 400,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "figure_label": "Daily rate",
        "filter_hash": FILTER_HASH,
        "explorer_href": "/app/explorer?from=2026-06-01",
        "source_keys": ["fixtures"],
        "items_observed": 400,
        "items_relevant": 120,
    }
    values.update(overrides)
    return CreateInsightRequest.model_validate(values)


# -- submissions ----------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://example.invalid/file",
        "not a url",
        "  ",
    ],
)
def test_a_non_http_submission_is_refused_at_the_boundary(url: str) -> None:
    with pytest.raises(ValidationError):
        SubmitUrlRequest(url=url)


def test_a_scheme_smuggled_behind_a_fragment_is_refused() -> None:
    """A partial pattern match would accept this; the anchored one does not."""
    with pytest.raises(ValidationError):
        SubmitUrlRequest(url="javascript:void#https://example.invalid")


def test_a_public_https_url_is_accepted() -> None:
    assert SubmitUrlRequest(url="https://example.invalid/story").url.startswith("https://")


def test_a_submission_rejects_an_unknown_field() -> None:
    """`extra="forbid"` is what stops a client from setting something we ignore."""
    with pytest.raises(ValidationError):
        SubmitUrlRequest.model_validate({"url": "https://example.invalid", "user_id": "x"})


# -- disputes -------------------------------------------------------------


def test_an_empty_dispute_reason_is_refused() -> None:
    with pytest.raises(ValidationError):
        OpenDisputeRequest(reason="")


# -- review decisions -----------------------------------------------------


def test_a_correction_without_labels_is_refused() -> None:
    with pytest.raises(ValidationError, match="corrected labels"):
        AppendDecisionRequest(decision=ReviewDecision.corrected)


def test_labels_on_a_confirmation_are_refused() -> None:
    """Otherwise a reviewer could smuggle a relabel in under `confirmed`."""
    with pytest.raises(ValidationError, match="corrected labels"):
        AppendDecisionRequest(
            decision=ReviewDecision.confirmed, corrected_labels={"stance": "uncertain"}
        )


def test_only_a_correction_may_be_a_training_candidate() -> None:
    """`spec.md` FR-DISPUTE-006. Flagging a confirmation would feed the model its
    own output back as training data."""
    with pytest.raises(ValidationError, match="training candidate"):
        AppendDecisionRequest(decision=ReviewDecision.confirmed, is_training_candidate=True)


def test_a_correction_may_be_quarantined_as_a_training_candidate() -> None:
    request = AppendDecisionRequest(
        decision=ReviewDecision.corrected,
        corrected_labels={"stance": "non_hateful_discussion"},
        is_training_candidate=True,
    )

    assert request.is_training_candidate is True


# -- prepared reports -----------------------------------------------------


def test_a_prepared_report_cannot_be_moved_back_to_prepared() -> None:
    with pytest.raises(ValidationError, match="back to prepared"):
        RecordOutcomeRequest(status=PreparedReportStatus.prepared)


def test_closing_a_report_needs_the_outcome() -> None:
    with pytest.raises(ValidationError, match="outcome"):
        RecordOutcomeRequest(status=PreparedReportStatus.closed)


def test_an_outcome_cannot_be_recorded_at_the_moment_of_filing() -> None:
    """Filing and hearing back are different events; collapsing them would let a
    record claim an outcome the platform has not given."""
    with pytest.raises(ValidationError, match="close the report"):
        RecordOutcomeRequest(
            status=PreparedReportStatus.submitted,
            outcome=PreparedReportOutcome.content_removed,
        )


def test_a_prepared_report_request_cannot_name_its_own_recipient() -> None:
    """FR-TOS-010: the address comes from the reviewed catalogue. A field for one
    here would make the endpoint a mail relay."""
    with pytest.raises(ValidationError):
        PrepareReportRequest.model_validate(
            {
                "content_item_id": "00000000-0000-0000-0000-000000000001",
                "platform_policy_id": "00000000-0000-0000-0000-000000000002",
                "policy_version": "2026.08.23",
                "evidence_summary": "Synthetic summary.",
                "suggested_text": "Synthetic wording.",
                "recipient_address": "attacker@example.invalid",
            }
        )


# -- insights and discussion ----------------------------------------------


def test_an_insight_numerator_may_not_exceed_its_denominator() -> None:
    with pytest.raises(ValidationError, match="numerator"):
        _insight(numerator=401, denominator=400)


def test_an_insight_window_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="window_start"):
        _insight(window_start=WINDOW_END, window_end=WINDOW_START)


def test_relevant_items_may_not_exceed_observed_items() -> None:
    with pytest.raises(ValidationError, match="items_relevant"):
        _insight(items_relevant=500, items_observed=400)


@pytest.mark.parametrize(
    "href",
    ["https://example.invalid/explorer", "//example.invalid", "app/explorer", ""],
)
def test_an_insight_link_must_be_first_party(href: str) -> None:
    """An absolute link would send a reader at somebody else's server, which is
    exactly the screenshot board ADR 0004 refused."""
    with pytest.raises(ValidationError):
        _insight(explorer_href=href)


def test_a_capture_image_must_be_first_party() -> None:
    with pytest.raises(ValidationError):
        CreateCaptureRequest(
            alt_text="Daily rate chart",
            image_source="https://example.invalid/screenshot.png",
            filter_hash=FILTER_HASH,
            explorer_href="/app/explorer",
        )


def test_a_capture_needs_alt_text() -> None:
    """A figure with no alt text is unusable to a reader who needs one."""
    with pytest.raises(ValidationError):
        CreateCaptureRequest(
            alt_text="",
            image_source="/media/figure.png",
            filter_hash=FILTER_HASH,
            explorer_href="/app/explorer",
        )


def test_an_empty_note_is_refused() -> None:
    with pytest.raises(ValidationError):
        CreatePostRequest(body="")


def test_an_insight_reports_a_gap_rather_than_a_zero_rate() -> None:
    """A zero denominator means nothing was observed. Publishing `0.0` would read
    as "no anti-Muslim content", which is a claim the data does not support."""
    summary = InsightSummary(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        author_id=UUID("00000000-0000-0000-0000-000000000002"),
        author_display_name=None,
        title="Empty window",
        claim="No items were observed in this window.",
        metric="likely_anti_muslim_rate",
        numerator=0,
        denominator=0,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        figure_label="Daily rate",
        filter_hash=FILTER_HASH,
        explorer_href="/app/explorer",
        source_keys=[],
        items_observed=0,
        items_relevant=0,
        created_at=WINDOW_END,
    )

    assert summary.value is None


# -- profile --------------------------------------------------------------


def test_a_profile_update_must_change_something() -> None:
    with pytest.raises(ValidationError, match="at least one field"):
        UpdateProfileRequest()


def test_a_profile_update_cannot_set_a_role() -> None:
    """Role comes from the verified token. A body field for it would let a client
    name its own privileges."""
    with pytest.raises(ValidationError):
        UpdateProfileRequest.model_validate({"role": "administrator"})


def test_a_profile_update_accepts_onboarding_progress() -> None:
    request = UpdateProfileRequest(onboarding_status=OnboardingStatus.completed)

    assert request.onboarding_status is OnboardingStatus.completed
