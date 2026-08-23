"""The job state machine, written once and shared by runs and jobs.

`spec.md` section 17.3 draws the graph; this module is that drawing as data, so
a transition is checked against one table rather than against whatever `if` a
caller happened to write. Everything not in the table is invalid, including the
tempting ones: a succeeded job never runs again, and a cancelled job is not
resurrected by a late worker that still holds a stale lease.
"""

from __future__ import annotations

from amanah.domain.enums import JobState

#: States a job can no longer leave. A terminal job is history.
TERMINAL_STATES: frozenset[JobState] = frozenset(
    {JobState.succeeded, JobState.failed, JobState.policy_blocked, JobState.cancelled}
)

#: States a worker may claim from once `available_at` has passed.
CLAIMABLE_STATES: frozenset[JobState] = frozenset({JobState.queued, JobState.retry_wait})

#: Every permitted move. A state absent from a value set cannot be reached from
#: that key, and `TERMINAL_STATES` all map to the empty set.
ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.queued: frozenset({JobState.running, JobState.cancelled, JobState.policy_blocked}),
    JobState.running: frozenset(
        {
            JobState.succeeded,
            JobState.retry_wait,
            JobState.failed,
            JobState.policy_blocked,
            JobState.cancelled,
            # Lease recovery: an expired claim returns the job to the queue with
            # its attempt count intact rather than losing the work.
            JobState.queued,
        }
    ),
    JobState.retry_wait: frozenset(
        {JobState.running, JobState.cancelled, JobState.failed, JobState.policy_blocked}
    ),
    JobState.succeeded: frozenset(),
    JobState.failed: frozenset(),
    JobState.policy_blocked: frozenset(),
    JobState.cancelled: frozenset(),
}


class InvalidJobTransitionError(RuntimeError):
    """A caller asked for a move the state machine does not allow.

    This is a programming error, not a user-correctable one, so it carries the
    states for the log and never reaches an API response body.
    """

    def __init__(self, current: JobState, requested: JobState) -> None:
        super().__init__(f"cannot move a job from {current.value} to {requested.value}")
        self.current = current
        self.requested = requested


def is_terminal(state: JobState) -> bool:
    """Whether the job has stopped for good."""
    return state in TERMINAL_STATES


def can_transition(current: JobState, requested: JobState) -> bool:
    """Whether the move is in the table."""
    return requested in ALLOWED_TRANSITIONS[current]


def assert_transition(current: JobState, requested: JobState) -> None:
    """Refuse an invalid move.

    Re-entering the same state is refused too. A worker that reports success
    twice is either a duplicate delivery — which the idempotency key already
    absorbed — or a bug, and both are better surfaced than absorbed here.
    """
    if not can_transition(current, requested):
        raise InvalidJobTransitionError(current, requested)
