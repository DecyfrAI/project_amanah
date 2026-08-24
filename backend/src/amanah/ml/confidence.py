"""Score-to-tier mapping and review routing (B-S14.3, B-S14.4, B-S14.6).

The thresholds below are **provisional**. They were chosen to be defensible
before calibration, not because any holdout said they are right, and
`CONFIDENCE_THRESHOLD_VERSION` carries `-provisional` so that fact travels with
every prediction rather than living in a comment. `spec.md` section 9.5 and
`rules/ml.md` both refuse an accuracy claim without a reviewed evaluation, so
nothing here should be read as one.

Routing to review is deliberately generous. A false negative in this product is
an unflagged piece of anti-Muslim rhetoric; a false positive is benign Muslim
speech labelled as hate. The second is the worse failure, so uncertainty, high
severity, and low confidence all route to a human rather than to a chart.
"""

from __future__ import annotations

from dataclasses import dataclass

from amanah.domain.enums import ConfidenceTier, Relevance, ReviewTaskType, Severity, Stance
from amanah.ml.taxonomy import ClassificationOutput
from amanah.ml.versions import CONFIDENCE_THRESHOLD_VERSION


@dataclass(frozen=True, slots=True)
class ConfidenceThresholds:
    """One versioned score-to-tier mapping.

    Configurable rather than constant because calibration will move these, and
    the version is part of the record so a moved threshold does not silently
    reinterpret predictions made under the old one.
    """

    version: str
    medium_at: float
    high_at: float

    def tier_for(self, score: float) -> ConfidenceTier:
        """Map a numeric score onto its display tier."""
        if score >= self.high_at:
            return ConfidenceTier.high
        if score >= self.medium_at:
            return ConfidenceTier.medium
        return ConfidenceTier.low


#: Provisional defaults. Calibrate against a reviewed holdout before treating a
#: tier as a quality statement (B-S14.4).
DEFAULT_THRESHOLDS = ConfidenceThresholds(
    version=CONFIDENCE_THRESHOLD_VERSION,
    medium_at=0.6,
    high_at=0.85,
)

#: Severity at or above which a human looks regardless of confidence. A threat is
#: the one label whose consequences do not wait for a calibration exercise.
REVIEW_SEVERITY_FLOOR = Severity.high


def review_reason(output: ClassificationOutput, tier: ConfidenceTier) -> ReviewTaskType | None:
    """Why this prediction needs a human, or `None` if it does not.

    Ordered by how much the answer is doubted: an explicitly uncertain model, then
    an unresolved relevance question, then a severe claim, then a weak score. The
    first match wins so the queue shows the most informative reason rather than
    whichever check happens to run last.
    """
    if output.is_uncertain:
        return ReviewTaskType.model_disagreement
    if output.relevance is Relevance.uncertain or output.stance is Stance.uncertain:
        return ReviewTaskType.uncertain_relevance
    if output.stance is Stance.likely_anti_muslim and output.severity >= REVIEW_SEVERITY_FLOOR:
        return ReviewTaskType.severity_escalation
    if tier is ConfidenceTier.low:
        return ReviewTaskType.low_confidence
    return None


#: Review priority by reason, highest first. A severe claim and a genuinely
#: ambiguous item are worth a reviewer's attention before a merely weak score.
REVIEW_PRIORITY: dict[ReviewTaskType, int] = {
    ReviewTaskType.dispute: 40,
    ReviewTaskType.severity_escalation: 30,
    ReviewTaskType.invalid_output: 20,
    ReviewTaskType.model_disagreement: 15,
    ReviewTaskType.uncertain_relevance: 10,
    ReviewTaskType.low_confidence: 5,
}
