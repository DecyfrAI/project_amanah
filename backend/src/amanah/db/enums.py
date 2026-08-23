"""Postgres enum types bound to the controlled vocabulary in `amanah.domain.enums`.

Every enum column uses a native Postgres type rather than free `text`, so an
unknown label is rejected by the database and not only by the application. The
Python enum is the single source of the label set: adding a member here and
running a migration are the only way a new value can exist.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SaEnum

from amanah.domain import enums as domain


def pg_enum(python_enum: type[StrEnum], name: str) -> SaEnum:
    """Map a `StrEnum` onto a native Postgres enum type.

    `values_callable` stores the enum *value* rather than the Python member name,
    so the database label and the JSON label published by the API are identical.
    `create_type=False` keeps type creation in migrations, where it belongs.
    """
    return SaEnum(
        python_enum,
        name=name,
        schema=None,
        native_enum=True,
        create_type=False,
        validate_strings=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


#: `(python enum, postgres type name)` for every enum the schema uses. The
#: migration builds its `CREATE TYPE` statements from this list, so a type can
#: never drift from the vocabulary it represents.
ENUM_TYPES: tuple[tuple[type[StrEnum], str], ...] = (
    (domain.SourceKind, "source_kind"),
    (domain.PublicPlatform, "public_platform"),
    (domain.ContentKind, "content_kind"),
    (domain.SourceStatus, "source_availability"),
    (domain.ConnectorStatus, "connector_status"),
    (domain.RetentionPolicy, "retention_policy"),
    (domain.SeedEntryKind, "seed_entry_kind"),
    (domain.SamplingStratum, "sampling_stratum"),
    (domain.ApprovalStatus, "approval_status"),
    (domain.CollectionMode, "collection_mode"),
    (domain.JobState, "job_state"),
    (domain.JobStage, "job_stage"),
    (domain.Relevance, "relevance"),
    (domain.Stance, "stance"),
    (domain.HateType, "hate_type"),
    (domain.ConfidenceTier, "confidence_tier"),
    (domain.InferenceStatus, "inference_status"),
    (domain.ReviewState, "review_state"),
    (domain.ReviewTaskType, "review_task_type"),
    (domain.ReviewTaskStatus, "review_task_status"),
    (domain.ReviewDecision, "review_decision"),
    (domain.MetricInterval, "metric_interval"),
    (domain.RelationBasis, "relation_basis"),
    (domain.RelationReviewState, "relation_review_state"),
    (domain.ValidationStatus, "validation_status"),
    (domain.Role, "user_role"),
    (domain.OnboardingStatus, "onboarding_status"),
    (domain.SubmissionStatus, "submission_status"),
    (domain.DisputeStatus, "dispute_status"),
    (domain.ContributionType, "contribution_type"),
    (domain.ContributionEventType, "contribution_event_type"),
    (domain.PublicationStatus, "publication_status"),
    (domain.PreparedReportStatus, "prepared_report_status"),
    (domain.PreparedReportOutcome, "prepared_report_outcome"),
    (domain.ResearchReportStatus, "research_report_status"),
    (domain.RedactionMode, "redaction_mode"),
    (domain.ResourceCategory, "resource_category"),
)

_TYPE_NAMES = {python_enum: name for python_enum, name in ENUM_TYPES}


def enum_column(python_enum: type[StrEnum]) -> SaEnum:
    """Return the mapped Postgres type for a registered domain enum."""
    return pg_enum(python_enum, _TYPE_NAMES[python_enum])
