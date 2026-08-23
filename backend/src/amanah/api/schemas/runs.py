"""Administrator views of collection runs and the jobs beneath them (B-S7.6).

These models describe operational state, not product data. They deliberately
carry no queue payload, no checkpoint, and no lease owner: an operator needs to
know which stage a run reached, how many attempts it has spent, and the safe code
it stopped on — not the contents of the message a worker was handed.
"""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from amanah.api.schemas.base import RequestModel, ResponseModel, UtcDatetime
from amanah.api.schemas.common import ResponseMeta
from amanah.domain.enums import CollectionMode, JobStage, JobState
from amanah.jobs.runs import MAXIMUM_ITEM_CAP

#: Ordering name carried by every admin run cursor: newest dispatch first.
RUN_ORDER_KEY = "run_started_at"

#: Modes an administrator may dispatch by hand. `scheduled` is absent on
#: purpose — that mode belongs to the scheduler, and letting a person claim it
#: would make run provenance a lie.
DISPATCHABLE_MODES = frozenset(
    {CollectionMode.manual, CollectionMode.backfill, CollectionMode.fixture}
)

#: Idempotency keys are caller-chosen and echoed back, so they are bounded and
#: restricted to characters that cannot confuse a log line.
IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9._:-]{8,200}$"


class BackgroundJobSummary(ResponseModel):
    """One checkpointed stage of a run."""

    id: UUID
    collection_run_id: UUID
    stage: JobStage
    state: JobState
    attempt: int = Field(ge=0)
    max_attempts: int = Field(gt=0)
    available_at: UtcDatetime
    safe_error_code: str | None = None
    is_dead_lettered: bool
    created_at: UtcDatetime
    completed_at: UtcDatetime | None = None


class CollectionRunSummary(ResponseModel):
    """One bounded execution of one adapter against one source."""

    id: UUID
    source_id: UUID
    source_key: str
    source_name: str
    source_seed_entry_id: UUID | None = None
    idempotency_key: str
    mode: CollectionMode
    adapter_version: str
    window_start: UtcDatetime | None = None
    window_end: UtcDatetime | None = None
    status: JobState
    counts: dict[str, int] = Field(
        default_factory=dict,
        description="Items discovered, fetched, stored, skipped, and deduplicated.",
    )
    coverage_warnings: list[str] = Field(
        default_factory=list,
        description="Publishable gap descriptions. Never a provider error body.",
    )
    safe_error_code: str | None = None
    item_cap: int | None = None
    attempt: int = Field(ge=0)
    max_attempts: int = Field(gt=0)
    next_run_at: UtcDatetime | None = None
    is_dead_lettered: bool
    started_at: UtcDatetime
    completed_at: UtcDatetime | None = None


class CollectionRunDetail(ResponseModel):
    """One run together with the stages it has produced so far."""

    run: CollectionRunSummary
    jobs: list[BackgroundJobSummary] = Field(default_factory=list)


class CollectionRunResponse(ResponseModel):
    """Envelope for a single run read or dispatch."""

    run: CollectionRunSummary
    jobs: list[BackgroundJobSummary] = Field(default_factory=list)
    meta: ResponseMeta


class CreateRunRequest(RequestModel):
    """An administrator's request to run one adapter once.

    The window and the cap are both bounded server-side. A dispatch that omits
    the cap gets the configured default rather than an unbounded run, because
    "collect everything" is never a safe instruction to a live provider.
    """

    source_key: str = Field(
        min_length=1,
        max_length=100,
        description="Stable configuration key of the source, not its identifier.",
    )
    mode: CollectionMode = CollectionMode.manual
    idempotency_key: str = Field(pattern=IDEMPOTENCY_KEY_PATTERN)
    window_start: UtcDatetime | None = None
    window_end: UtcDatetime | None = None
    item_cap: int | None = Field(default=None, gt=0, le=MAXIMUM_ITEM_CAP)
    source_seed_entry_id: UUID | None = None

    @model_validator(mode="after")
    def _check_mode_and_window(self) -> Self:
        if self.mode not in DISPATCHABLE_MODES:
            raise ValueError("that mode cannot be dispatched by hand")
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("a window needs both a start and an end")
        if (
            self.window_start is not None
            and self.window_end is not None
            and self.window_end < self.window_start
        ):
            raise ValueError("window_end must not be before window_start")
        return self
