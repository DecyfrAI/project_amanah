"""The reviewed platform-policy catalogue and how a candidate is chosen (B-S18.1, B-S18.2).

Two things live here and the separation matters.

`PolicyCatalogue` is reviewed configuration loaded from `config/platform-policies.yml`
and projected into `platform_policies`. Only a published entry is offered, and
only a person's review can publish one, so the assistant can never invent a rule
or cite an unreviewed summary.

`PolicyMatcher` decides which catalogued rules are *plausible* for one item. The
implementation shipped here is deterministic: it reads the stored prediction's
hate types and severity and scores the rules whose subject matter overlaps. It
produces `possible policy match` and nothing stronger — `spec.md` section 8.4
forbids claiming a violation with certainty, and B-S18.3 requires a human to
confirm a rule before anything is prepared, so the score orders a short list for
a person rather than deciding anything.

The `PolicyMatcher` protocol is the seam for B-S13. When the controlled Gemini
client lands, a model-backed ranker implements the same three-method contract and
the routes do not change. It would rank and draft wording within the same rules:
catalogue entries only, structured output validated, uncertainty preserved, human
confirmation still required.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.reporting import PlatformPolicy
from amanah.domain.enums import (
    ConfidenceTier,
    HateType,
    PublicationStatus,
    ReportRecipientKind,
    Severity,
    Stance,
)
from amanah.ingestion.configuration import ConfigurationError, config_directory

logger = logging.getLogger(__name__)

POLICIES_FILENAME = "platform-policies.yml"

#: Version recorded on every match this deterministic matcher produces. It names
#: the matcher, not a model: nothing here is inferred, and a stored match must
#: say which code produced it so a later model-backed ranker is distinguishable.
DETERMINISTIC_MATCHER_VERSION = "catalogue-rules-1.0.0"

#: Score floor below which a rule is not offered at all. A list of weak guesses
#: is worse than a short list, because a user asked to confirm one of five
#: irrelevant rules will confirm the first.
MINIMUM_OFFERED_SCORE = 0.3

#: How the deterministic score maps onto the tier a reader is shown. The bands
#: are deliberately conservative: nothing here reaches `high`, because a rule
#: match derived from a taxonomy overlap is not high-confidence evidence of a
#: policy violation and must not be displayed as though it were.
_HIGH_SCORE = 0.75
_MEDIUM_SCORE = 0.5


class PolicyEntry(BaseModel):
    """One reviewed policy in the catalogue file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    platform: str = Field(min_length=1, max_length=50)
    policy_key: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1)
    official_url: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    version: str = Field(min_length=1, max_length=50)
    last_reviewed_at: date | None = None
    reviewed_by: str | None = None
    status: PublicationStatus = PublicationStatus.draft
    recipient_kind: ReportRecipientKind = ReportRecipientKind.official_form
    official_report_url: str | None = None
    report_email: str | None = None
    matches_hate_types: tuple[HateType, ...] = ()
    minimum_severity: int = Field(default=1, ge=0, le=int(Severity.high))

    @model_validator(mode="after")
    def _check_publishable(self) -> Self:
        if not self.official_url.startswith("https://"):
            raise ValueError("official_url must be an absolute https URL")
        if self.status is PublicationStatus.published and (
            self.reviewed_by is None or self.last_reviewed_at is None
        ):
            raise ValueError("a published policy needs a reviewer and a review date")
        wants_form = self.recipient_kind is ReportRecipientKind.official_form
        # A channel never carries the other channel's destination.
        if wants_form and self.report_email is not None:
            raise ValueError("a form platform must not carry report_email")
        if not wants_form and self.official_report_url is not None:
            raise ValueError("an email platform must not carry official_report_url")
        # Completeness is required to publish, not to draft.
        if self.status is PublicationStatus.published:
            if wants_form and self.official_report_url is None:
                raise ValueError("a published form platform needs official_report_url")
            if not wants_form and self.report_email is None:
                raise ValueError("a published email platform needs report_email")
        if self.official_report_url is not None and not self.official_report_url.startswith(
            "https://"
        ):
            raise ValueError("official_report_url must be an absolute https URL")
        return self


class PolicyCatalogue(BaseModel):
    """The whole reviewed file, with its configuration version."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config_version: str = Field(min_length=1, max_length=50)
    policies: tuple[PolicyEntry, ...]

    @model_validator(mode="after")
    def _check_unique(self) -> Self:
        seen: set[tuple[str, str, str]] = set()
        for policy in self.policies:
            key = (policy.platform, policy.policy_key, policy.version)
            if key in seen:
                raise ValueError(f"duplicate policy {key}")
            seen.add(key)
        return self


def load_policy_catalogue(directory: Path | None = None) -> PolicyCatalogue:
    """Read and validate the reviewed catalogue, or fail with a safe message."""
    path = config_directory(directory) / POLICIES_FILENAME
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"policy catalogue is unreadable at {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"policy catalogue at {path} is not valid YAML") from exc
    try:
        return PolicyCatalogue.model_validate(document)
    except ValueError as exc:
        raise ConfigurationError(f"policy catalogue at {path} is invalid: {exc}") from exc


def project_policies(session: Session, catalogue: PolicyCatalogue) -> int:
    """Write the reviewed catalogue into `platform_policies`.

    Idempotent on `(platform, policy_key, version)`, which is the identity
    `spec.md` section 14.6 requires: a re-reviewed rule under a new version is a
    new row, so a prepared report that froze the old version still resolves.
    """
    written = 0
    for policy in catalogue.policies:
        values: dict[str, Any] = {
            "platform": policy.platform,
            "policy_key": policy.policy_key,
            "title": policy.title,
            "official_url": policy.official_url,
            "summary": policy.summary,
            "version": policy.version,
            "last_reviewed_at": _as_datetime(policy.last_reviewed_at),
            "status": policy.status,
            "reviewed_by": policy.reviewed_by,
            "recipient_kind": policy.recipient_kind,
            "official_report_url": policy.official_report_url,
            "report_email": policy.report_email,
        }
        session.execute(
            insert(PlatformPolicy)
            .values(**values)
            .on_conflict_do_update(
                constraint="platform_policies_platform_policy_key_version_unique",
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"platform", "policy_key", "version"}
                },
            )
        )
        written += 1
    session.commit()
    logger.info("policy catalogue projected", extra={"policies": written})
    return written


class PolicyCandidate(BaseModel):
    """One rule offered to a user, with the uncertainty that goes with it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    platform_policy_id: Any
    platform: str
    policy_key: str
    title: str
    summary: str
    official_url: str
    version: str
    last_reviewed_at: datetime | None
    recipient_kind: ReportRecipientKind
    official_report_url: str | None
    score: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    rationale: str


class PolicyMatcher(Protocol):
    """What any policy matcher must provide.

    Written as a protocol so the controlled Gemini client (B-S13) can supply a
    model-backed ranker later without the routes changing. Any implementation is
    bound by the same rules: only catalogued rules, uncertainty preserved, and a
    human confirmation before anything is prepared.
    """

    @property
    def matcher_version(self) -> str:
        """Version recorded on every stored match."""

    def candidates(
        self,
        *,
        platform: str,
        hate_types: tuple[HateType, ...],
        severity: int,
        stance: Stance,
    ) -> tuple[PolicyCandidate, ...]:
        """Plausible rules for one classified item, strongest first."""


class CataloguePolicyMatcher:
    """Deterministic matching from the stored prediction to catalogued rules."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._rules = {
            (entry.platform, entry.policy_key): entry for entry in load_policy_catalogue().policies
        }

    @property
    def matcher_version(self) -> str:
        return DETERMINISTIC_MATCHER_VERSION

    def candidates(
        self,
        *,
        platform: str,
        hate_types: tuple[HateType, ...],
        severity: int,
        stance: Stance,
    ) -> tuple[PolicyCandidate, ...]:
        """Score the published rules for this platform against the prediction.

        An item the classifier did not read as anti-Muslim gets nothing. Offering
        a policy match for counterspeech, a quotation, or neutral reporting would
        turn the assistant into a way to report people for discussing the subject,
        which is precisely the outcome `AGENTS.md` forbids.
        """
        if stance is not Stance.likely_anti_muslim or not hate_types:
            return ()

        scored: list[PolicyCandidate] = []
        for row in self._published_rules(platform):
            entry = self._rules.get((row.platform, row.policy_key))
            if entry is None:
                # In the database but not in the reviewed file: the file is the
                # authority on what may be offered.
                continue
            score = _score(entry, hate_types=hate_types, severity=severity)
            if score < MINIMUM_OFFERED_SCORE:
                continue
            scored.append(
                PolicyCandidate(
                    platform_policy_id=row.id,
                    platform=row.platform,
                    policy_key=row.policy_key,
                    title=row.title,
                    summary=row.summary,
                    official_url=row.official_url,
                    version=row.version,
                    last_reviewed_at=row.last_reviewed_at,
                    recipient_kind=ReportRecipientKind(row.recipient_kind),
                    official_report_url=row.official_report_url,
                    score=score,
                    confidence_tier=_tier(score),
                    rationale=_rationale(entry, hate_types=hate_types),
                )
            )
        scored.sort(key=lambda candidate: (-candidate.score, candidate.policy_key))
        return tuple(scored)

    def _published_rules(self, platform: str) -> tuple[PlatformPolicy, ...]:
        """Only published rows. A draft is not something a user may be offered."""
        statement = select(PlatformPolicy).where(
            PlatformPolicy.platform == platform,
            PlatformPolicy.status == PublicationStatus.published,
        )
        return tuple(self._session.execute(statement).scalars().all())


def _score(entry: PolicyEntry, *, hate_types: tuple[HateType, ...], severity: int) -> float:
    """Overlap between what the rule is about and what the classifier found.

    Deliberately simple arithmetic over two stored fields. It exists to put the
    most plausible two or three rules in front of a person, and a more elaborate
    formula would only make the number look more authoritative than it is.
    """
    if severity < entry.minimum_severity:
        return 0.0
    overlap = set(hate_types) & set(entry.matches_hate_types)
    if not overlap:
        return 0.0
    coverage = len(overlap) / len(hate_types)
    # Severity above the rule's floor raises confidence a little, capped so no
    # deterministic match can present itself as near-certain.
    headroom = min(severity - entry.minimum_severity, int(Severity.high)) * 0.1
    return round(min(0.4 + coverage * 0.4 + headroom, _HIGH_SCORE), 3)


def _tier(score: float) -> ConfidenceTier:
    if score >= _HIGH_SCORE:
        return ConfidenceTier.high
    if score >= _MEDIUM_SCORE:
        return ConfidenceTier.medium
    return ConfidenceTier.low


def _rationale(entry: PolicyEntry, *, hate_types: tuple[HateType, ...]) -> str:
    """One sentence a reader can check, phrased as a possibility.

    `spec.md` section 8.4: "possible policy match" until a human or the platform
    confirms it. The wording never asserts a violation.
    """
    overlap = sorted(kind.value for kind in set(hate_types) & set(entry.matches_hate_types))
    subjects = ", ".join(name.replace("_", " ") for name in overlap)
    return (
        f"Possible match: this item was classified as {subjects}, which is the "
        f"subject matter of {entry.title}. A person must confirm the rule applies."
    )


def _as_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
