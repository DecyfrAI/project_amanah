"""Background jobs: one row per checkpointed stage of one collection run.

A job is the unit a worker claims. Claiming is a lease rather than a delete, so
a worker that dies mid-stage loses its lease and the job returns to the queue
with its attempt count intact instead of vanishing.

`idempotency_key` is the natural key of the work, not of the delivery: the same
stage of the same run over the same partition produces the same key, so a
duplicate dispatch finds the existing row rather than creating a second one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UpdatedAt, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.domain.enums import JobStage, JobState

if TYPE_CHECKING:
    from amanah.db.models.content import CollectionRun


class BackgroundJob(Base):
    """One attemptable stage of one collection run."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="background_jobs_idempotency_key_unique"),
        CheckConstraint("attempt >= 0", name="attempt_non_negative"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        # A lease is an owner *and* an expiry or neither. Half a lease would be
        # either an unreclaimable job or an unattributable one.
        CheckConstraint(
            "(lease_owner IS NULL) = (lease_expires_at IS NULL)",
            name="lease_complete",
        ),
        # Running means someone holds it. Without this a crashed transition
        # could leave a job that no recovery sweep would ever notice.
        CheckConstraint(
            "state <> 'running' OR lease_owner IS NOT NULL",
            name="running_requires_lease",
        ),
        CheckConstraint(
            "state IN ('queued', 'running', 'retry_wait') OR completed_at IS NOT NULL",
            name="terminal_requires_completion",
        ),
        # Dead-lettering is what exhausting the retry budget looks like; it is
        # never a state a job can be parked in while still runnable.
        CheckConstraint(
            "NOT is_dead_lettered OR state = 'failed'",
            name="dead_letter_requires_failure",
        ),
        # The claim query: runnable jobs whose backoff has elapsed, oldest first.
        Index(
            "background_jobs_state_available_at_idx",
            "state",
            "available_at",
            postgresql_where=text("state IN ('queued', 'retry_wait')"),
        ),
        # The lease-recovery sweep.
        Index(
            "background_jobs_lease_expires_at_idx",
            "lease_expires_at",
            postgresql_where=text("state = 'running'"),
        ),
        Index("background_jobs_collection_run_id_stage_idx", "collection_run_id", "stage"),
    )

    id: Mapped[UuidPrimaryKey]
    collection_run_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[JobStage] = mapped_column(enum_column(JobStage), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        doc="Natural key of the work: run, stage, and partition. Never a delivery id.",
    )
    state: Mapped[JobState] = mapped_column(
        enum_column(JobState), nullable=False, server_default="queued"
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))
    available_at: Mapped[CreatedAt] = mapped_column(
        doc="Earliest time a worker may claim this job; moved forward by backoff."
    )
    lease_owner: Mapped[str | None] = mapped_column(
        String(200), doc="Opaque worker identifier. Never a host name or a credential."
    )
    lease_expires_at: Mapped[Timestamp | None]
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc=(
            "Stage input written by the previous stage. It can carry provider "
            "metadata for the one item being processed, so it is excluded from "
            "every projection and is never published."
        ),
    )
    checkpoint: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Stage output, written before the next stage is enqueued.",
    )
    safe_error_code: Mapped[str | None] = mapped_column(
        String(100), doc="Stable code only; never a provider or driver message."
    )
    is_dead_lettered: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
    completed_at: Mapped[Timestamp | None]

    collection_run: Mapped[CollectionRun] = relationship(back_populates="jobs")
