"""Staged classification and prediction persistence (B-S14).

Two rules govern the writes here.

*Predictions are history.* A row is keyed by content item plus the model, model
version, and prompt version that produced it. Re-running the same versions
converges on the same row, which makes a retry idempotent; running a *new* version
adds a row, so the prediction a published figure cited stays exactly as it was.
Nothing in this module updates a label.

*A non-answer is still a record.* A deferred, policy-blocked, invalid, or failed
inference writes a prediction with that status rather than nothing at all. The
alternative — no row — is indistinguishable from "not yet processed", and the
dashboard would count the item as unanalysed forever while the pipeline kept
skipping it. The database check constraint refuses a hate claim on any row whose
status is not `succeeded`, so a non-answer cannot become a finding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.canonical.text import NORMALIZATION_VERSION
from amanah.db.models.analysis import Prediction, ReviewTask
from amanah.domain.enums import (
    ConfidenceTier,
    InferenceStatus,
    PublicPlatform,
    Relevance,
    RetentionPolicy,
    ReviewTaskStatus,
    ReviewTaskType,
    Severity,
    Stance,
)
from amanah.ml.catalog import CLASSIFY_TEXT_PROMPT, CLASSIFY_TEXT_PROMPT_ID
from amanah.ml.confidence import (
    DEFAULT_THRESHOLDS,
    REVIEW_PRIORITY,
    ConfidenceThresholds,
    review_reason,
)
from amanah.ml.gemini import GeminiClient, InferenceRequest
from amanah.ml.policy import DataClass, TransferRequest
from amanah.ml.results import (
    InferenceFailure,
    InferenceResult,
    InferenceSuccess,
    failure_reason,
)
from amanah.ml.taxonomy import ClassificationOutput
from amanah.ml.versions import TAXONOMY_VERSION

logger = logging.getLogger(__name__)

#: Model version recorded alongside the model name. The provider does not report
#: a build identifier on the generate endpoint, so the configured model string is
#: the version, and this constant records which of our own call conventions
#: produced the row.
CALL_CONVENTION_VERSION = "v1"

#: Score stored for a prediction that has no labels. Zero rather than null so the
#: column stays non-null and every sort over it is defined; the `inference_status`
#: column is what says the score means nothing.
NON_ANSWER_SCORE = 0.0


@dataclass(frozen=True, slots=True)
class ClassifiableItem:
    """One item's model input and the provenance the transfer gate needs.

    Assembled by the caller from a canonical row rather than read here, so this
    service has no opinion about where text lives and stays testable without a
    database.
    """

    content_item_id: UUID
    content_hash: str
    model_text: str
    transfer: TransferRequest


@dataclass(frozen=True, slots=True)
class ClassificationRecord:
    """What one classification wrote."""

    prediction_id: UUID
    status: InferenceStatus
    requires_review: bool
    review_task_id: UUID | None


def build_model_input(*, normalized_text: str | None, context: dict[str, Any]) -> str:
    """Assemble the text the classifier sees, context first.

    A comment read without its parent is a different item from the same comment
    read under it, so the bounded context the canonical layer already assembled is
    labelled and prepended. The labels are plain because the model is told, in the
    system instruction, that all of this is data.
    """
    sections: list[str] = []
    for label, key in (
        ("Title", "title"),
        ("In reply to", "parent_text"),
        ("Thread opener", "root_text"),
        ("Caption", "caption"),
    ):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            sections.append(f"{label}: {value.strip()}")
    sections.append(f"Item: {(normalized_text or '').strip()}")
    return "\n\n".join(sections)


class ClassificationService:
    """Classifies canonical items and records what happened."""

    def __init__(
        self,
        session: Session,
        *,
        client: GeminiClient,
        thresholds: ConfidenceThresholds = DEFAULT_THRESHOLDS,
    ) -> None:
        self._session = session
        self._client = client
        self._thresholds = thresholds

    def classify(self, item: ClassifiableItem) -> ClassificationRecord:
        """Run one staged classification and persist the outcome."""
        result = self._client.infer(
            InferenceRequest(
                prompt_id=CLASSIFY_TEXT_PROMPT_ID,
                content=item.model_text,
                content_hash=item.content_hash,
                transfer=item.transfer,
            ),
            ClassificationOutput,
        )
        return self._persist(item, result)

    def _persist(
        self, item: ClassifiableItem, result: InferenceResult[ClassificationOutput]
    ) -> ClassificationRecord:
        if isinstance(result, InferenceSuccess):
            return self._persist_labels(item, result)
        return self._persist_non_answer(item, result)

    def _persist_labels(
        self, item: ClassifiableItem, result: InferenceSuccess[ClassificationOutput]
    ) -> ClassificationRecord:
        output = result.payload
        tier = self._thresholds.tier_for(output.score)
        reason = review_reason(output, tier)

        prediction_id = self._upsert_prediction(
            item,
            model_name=result.model_name,
            prompt_version=result.prompt_version,
            relevance=output.relevance,
            stance=output.stance,
            hate_types=[hate_type.value for hate_type in output.hate_types],
            severity=int(output.severity),
            narrative_tags=list(output.narrative_tags),
            score=output.score,
            confidence_tier=tier,
            rationale=output.rationale,
            requires_review=reason is not None,
            review_reason=reason.value if reason is not None else None,
            inference_status=InferenceStatus.succeeded,
        )
        task_id = (
            self._open_review_task(item.content_item_id, prediction_id, reason)
            if reason is not None
            else None
        )
        return ClassificationRecord(
            prediction_id=prediction_id,
            status=InferenceStatus.succeeded,
            requires_review=reason is not None,
            review_task_id=task_id,
        )

    def _persist_non_answer(
        self, item: ClassifiableItem, failure: InferenceFailure
    ) -> ClassificationRecord:
        """Record that no labels were produced, and why.

        Invalid output is the only non-answer that reaches a human. A spent budget
        or an unreachable provider will resolve on the next run; a model that
        stopped honouring its schema will not, and someone should know.
        """
        reason = failure_reason(failure)
        status = failure.status
        needs_review = status is InferenceStatus.invalid_output

        prediction_id = self._upsert_prediction(
            item,
            model_name=self._client.model_name,
            # A non-answer still records the prompt it would have used, so a
            # deferred item reprocessed after a prompt change lands on a new row
            # rather than overwriting the record of the deferral.
            prompt_version=CLASSIFY_TEXT_PROMPT.version,
            relevance=Relevance.uncertain,
            stance=Stance.uncertain,
            hate_types=[],
            severity=int(Severity.none),
            narrative_tags=[],
            score=NON_ANSWER_SCORE,
            confidence_tier=ConfidenceTier.low,
            rationale=None,
            requires_review=needs_review,
            review_reason=reason,
            inference_status=status,
        )
        logger.info(
            "classification produced no labels",
            extra={"status": status.value, "reason": reason},
        )
        task_id = (
            self._open_review_task(
                item.content_item_id, prediction_id, ReviewTaskType.invalid_output
            )
            if needs_review
            else None
        )
        return ClassificationRecord(
            prediction_id=prediction_id,
            status=status,
            requires_review=needs_review,
            review_task_id=task_id,
        )

    def _upsert_prediction(
        self,
        item: ClassifiableItem,
        *,
        model_name: str,
        prompt_version: str,
        relevance: Relevance,
        stance: Stance,
        hate_types: list[str],
        severity: int,
        narrative_tags: list[str],
        score: float,
        confidence_tier: ConfidenceTier,
        rationale: str | None,
        requires_review: bool,
        review_reason: str | None,
        inference_status: InferenceStatus,
    ) -> UUID:
        """Write one prediction, idempotently for its version triple.

        The conflict target is the documented unique constraint on
        `(content_item_id, model_name, model_version, prompt_version)`. A retry of
        the same versions refreshes the row it already produced; a different
        version does not collide and therefore adds history.
        """
        table = cast(Table, Prediction.__table__)
        values: dict[str, Any] = {
            "content_item_id": item.content_item_id,
            "model_name": model_name,
            "model_version": CALL_CONVENTION_VERSION,
            "prompt_version": prompt_version,
            "taxonomy_version": TAXONOMY_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "relevance": relevance.value,
            "stance": stance.value,
            "hate_types": hate_types,
            "severity": severity,
            "narrative_tags": narrative_tags,
            "score": score,
            "confidence_tier": confidence_tier.value,
            "confidence_threshold_version": self._thresholds.version,
            "rationale": rationale,
            "requires_review": requires_review,
            "review_reason": review_reason,
            "inference_status": inference_status.value,
            "inferred_at": datetime.now(UTC),
        }
        refreshable = {
            table.c[column]: values[column]
            for column in (
                "relevance",
                "stance",
                "hate_types",
                "severity",
                "narrative_tags",
                "score",
                "confidence_tier",
                "confidence_threshold_version",
                "rationale",
                "requires_review",
                "review_reason",
                "inference_status",
                "inferred_at",
                "normalization_version",
                "taxonomy_version",
            )
        }
        statement: Any = (
            insert(table)
            .values(**values)
            .on_conflict_do_update(
                constraint="predictions_content_item_model_prompt_version_unique",
                set_=refreshable,
            )
            .returning(table.c.id)
        )
        return cast(UUID, self._session.execute(statement).scalar_one())

    def _open_review_task(
        self, content_item_id: UUID, prediction_id: UUID, task_type: ReviewTaskType
    ) -> UUID:
        """Queue a human look, joining an existing open task rather than piling on.

        The database enforces one open task per prediction and type through a
        partial unique index. Checking first is what turns that guarantee into a
        returned identifier instead of an integrity error on a retry.
        """
        existing = self._session.execute(
            select(ReviewTask.id).where(
                ReviewTask.prediction_id == prediction_id,
                ReviewTask.task_type == task_type,
                ReviewTask.status.in_((ReviewTaskStatus.open, ReviewTaskStatus.claimed)),
            )
        ).scalar_one_or_none()
        if existing is not None:
            return cast(UUID, existing)

        task = ReviewTask(
            content_item_id=content_item_id,
            prediction_id=prediction_id,
            task_type=task_type,
            reason=REVIEW_REASONS[task_type],
            priority=REVIEW_PRIORITY[task_type],
            status=ReviewTaskStatus.open,
        )
        self._session.add(task)
        self._session.flush()
        return task.id


#: Plain-language queue text. Written for the reviewer who picks the task up, and
#: kept out of the model's hands so a rationale cannot become the reason a task
#: exists.
REVIEW_REASONS: dict[ReviewTaskType, str] = {
    ReviewTaskType.dispute: "A user disputed this classification.",
    ReviewTaskType.low_confidence: (
        "The model's confidence in this stance is below the medium tier threshold."
    ),
    ReviewTaskType.severity_escalation: (
        "The model reported a severe anti-Muslim harm band, which is confirmed by a person "
        "before it is treated as established."
    ),
    ReviewTaskType.model_disagreement: "The model flagged this item as one a person should decide.",
    ReviewTaskType.uncertain_relevance: (
        "The model could not determine whether this item is about Muslims or Islam, or what "
        "stance it takes."
    ),
    ReviewTaskType.invalid_output: (
        "The model returned output that did not match the required schema."
    ),
}


def transfer_for(
    *,
    platform: PublicPlatform,
    retention_policy: RetentionPolicy,
    is_fixture: bool,
    has_permitted_excerpt_only: bool,
) -> TransferRequest:
    """Describe one item's material for the transfer gate.

    An item whose licence allowed only an excerpt is a different data class from
    one whose full text was permitted, and the gate treats them separately.
    """
    return TransferRequest(
        data_class=(
            DataClass.permitted_excerpt if has_permitted_excerpt_only else DataClass.collected_text
        ),
        platform=platform,
        retention_policy=retention_policy,
        is_fixture=is_fixture,
    )
