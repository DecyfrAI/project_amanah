"""Collection-run and background-job state machines (B-S7).

`states` holds the transition table, `backoff` the retry schedule, `service` the
job queue, and `runs` the run lifecycle. Adapters in `amanah.ingestion` supply
the work; nothing here knows what a provider looks like.
"""

from amanah.jobs.backoff import next_attempt_at, retry_delay_seconds
from amanah.jobs.runs import (
    DEFAULT_ITEM_CAP,
    MAXIMUM_ITEM_CAP,
    MAXIMUM_WINDOW_DAYS,
    CollectionRunService,
    RunDispatch,
    RunValidationError,
    validate_dispatch,
)
from amanah.jobs.service import (
    DEFAULT_LEASE_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    JobService,
    LeaseLostError,
)
from amanah.jobs.states import (
    ALLOWED_TRANSITIONS,
    CLAIMABLE_STATES,
    TERMINAL_STATES,
    InvalidJobTransitionError,
    assert_transition,
    can_transition,
    is_terminal,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CLAIMABLE_STATES",
    "DEFAULT_ITEM_CAP",
    "DEFAULT_LEASE_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "MAXIMUM_ITEM_CAP",
    "MAXIMUM_WINDOW_DAYS",
    "TERMINAL_STATES",
    "CollectionRunService",
    "InvalidJobTransitionError",
    "JobService",
    "LeaseLostError",
    "RunDispatch",
    "RunValidationError",
    "assert_transition",
    "can_transition",
    "is_terminal",
    "next_attempt_at",
    "retry_delay_seconds",
    "validate_dispatch",
]
