"""The reviewed policy catalogue and deterministic matching (B-S18.1, B-S18.2).

No database and no model. What these prove is the shape of the offer: only
reviewed rules, never a certainty claim, and nothing at all for content the
classifier did not read as anti-Muslim.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    PublicationStatus,
    ReportRecipientKind,
    Severity,
)
from amanah.ingestion.configuration import ConfigurationError
from amanah.reporting.policies import (
    MINIMUM_OFFERED_SCORE,
    PolicyCatalogue,
    PolicyEntry,
    _score,
    _tier,
    load_policy_catalogue,
)

REPOSITORY_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _entry(**overrides: object) -> PolicyEntry:
    values: dict[str, object] = {
        "platform": "youtube",
        "policy_key": "hate_speech",
        "title": "Hate speech policy",
        "official_url": "https://example.invalid/policy",
        "summary": "Synthetic placeholder summary for tests.",
        "version": "2026.01.01",
        "matches_hate_types": (HateType.derogation, HateType.dehumanization),
        "minimum_severity": 1,
        "official_report_url": "https://example.invalid/report",
    }
    values.update(overrides)
    return PolicyEntry.model_validate(values)


def test_the_shipped_catalogue_loads_and_is_reviewed() -> None:
    """B-S18.1 wants at least one reviewer-approved entry with a review date."""
    catalogue = load_policy_catalogue(REPOSITORY_CONFIG)

    published = [
        entry for entry in catalogue.policies if entry.status is PublicationStatus.published
    ]
    assert published, "the catalogue must publish at least one reviewed rule"
    for entry in published:
        assert entry.reviewed_by is not None
        assert entry.last_reviewed_at is not None
        assert entry.official_url.startswith("https://")


def test_the_catalogue_covers_both_reporting_channels() -> None:
    """FR-TOS-010: a form platform and a no-form platform are both represented."""
    kinds = {entry.recipient_kind for entry in load_policy_catalogue(REPOSITORY_CONFIG).policies}

    assert ReportRecipientKind.official_form in kinds
    assert ReportRecipientKind.allowlist_email in kinds


def test_a_published_entry_without_a_reviewer_is_refused() -> None:
    with pytest.raises(ValueError, match="reviewer"):
        _entry(status=PublicationStatus.published, reviewed_by=None, last_reviewed_at=None)


def test_a_published_form_platform_must_carry_its_reporting_url() -> None:
    """FR-TOS-005 requires linking to the platform's own flow, so an entry that
    cannot do that must not reach a user."""
    with pytest.raises(ValueError, match="official_report_url"):
        _entry(
            status=PublicationStatus.published,
            reviewed_by="reviewer",
            last_reviewed_at=date(2026, 8, 23),
            official_report_url=None,
        )


def test_a_draft_may_still_be_missing_its_destination() -> None:
    """A draft exists because a reviewer has not finished it. Demanding the URL
    at insert would make an in-progress entry unrepresentable."""
    entry = _entry(official_report_url=None)

    assert entry.status is PublicationStatus.draft
    assert entry.official_report_url is None


def test_a_published_email_platform_must_carry_an_allow_listed_address() -> None:
    """The address can only come from review. Publishing with none would be a
    draft with nowhere safe to go."""
    with pytest.raises(ValueError, match="report_email"):
        _entry(
            status=PublicationStatus.published,
            reviewed_by="reviewer",
            last_reviewed_at=date(2026, 8, 23),
            recipient_kind=ReportRecipientKind.allowlist_email,
            official_report_url=None,
            report_email=None,
        )


def test_an_email_platform_must_not_also_claim_a_form() -> None:
    """Whatever its status: the two channels must never be confused."""
    with pytest.raises(ValueError, match="official_report_url"):
        _entry(
            recipient_kind=ReportRecipientKind.allowlist_email,
            official_report_url="https://example.invalid/report",
            report_email="reviewers@example.invalid",
        )


def test_a_form_platform_must_not_carry_an_address() -> None:
    with pytest.raises(ValueError, match="report_email"):
        _entry(report_email="reviewers@example.invalid")


def test_a_plain_http_policy_url_is_refused() -> None:
    with pytest.raises(ValueError, match="https"):
        _entry(official_url="http://example.invalid/policy")


def test_two_entries_with_the_same_platform_key_and_version_are_refused() -> None:
    """`spec.md` section 14.6 makes that triple the identity of a policy version."""
    with pytest.raises(ValueError, match="duplicate policy"):
        PolicyCatalogue.model_validate(
            {
                "config_version": "2026.01.01",
                "policies": [
                    _entry().model_dump(mode="json"),
                    _entry().model_dump(mode="json"),
                ],
            }
        )


def test_a_missing_catalogue_file_fails_with_a_safe_message(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="unreadable"):
        load_policy_catalogue(tmp_path)


def test_a_rule_below_its_severity_floor_scores_nothing() -> None:
    """A rule about severe content must not be offered for a mild item."""
    entry = _entry(minimum_severity=int(Severity.moderate))

    assert _score(entry, hate_types=(HateType.derogation,), severity=int(Severity.low)) == 0.0


def test_a_rule_with_no_overlapping_subject_scores_nothing() -> None:
    entry = _entry(matches_hate_types=(HateType.threat_or_incitement,))

    assert _score(entry, hate_types=(HateType.derogation,), severity=int(Severity.high)) == 0.0


def test_a_full_overlap_scores_above_the_offer_floor() -> None:
    entry = _entry()

    score = _score(entry, hate_types=(HateType.derogation,), severity=int(Severity.low))

    assert score >= MINIMUM_OFFERED_SCORE


def test_no_deterministic_score_reaches_certainty() -> None:
    """A taxonomy overlap is not strong evidence of a policy violation, and the
    tier a reader sees must never imply that it is."""
    entry = _entry(minimum_severity=0)

    score = _score(
        entry,
        hate_types=(HateType.derogation, HateType.dehumanization),
        severity=int(Severity.high),
    )

    assert score <= 0.75
    assert _tier(score) in {ConfidenceTier.low, ConfidenceTier.medium, ConfidenceTier.high}
    assert score < 1.0
