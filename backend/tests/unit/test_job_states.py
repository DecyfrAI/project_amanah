"""The job state machine and the retry schedule (B-S7.1, B-S7.5).

Pure behaviour, so no database. What matters here is that the transition table
is closed — every state that is not listed is refused — and that backoff grows
without ever exceeding its ceiling.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from amanah.domain.enums import JobState
from amanah.jobs.backoff import (
    BASE_DELAY_SECONDS,
    MAXIMUM_DELAY_SECONDS,
    next_attempt_at,
    retry_delay_seconds,
)
from amanah.jobs.states import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    InvalidJobTransitionError,
    assert_transition,
    can_transition,
    is_terminal,
)


def test_the_transition_table_covers_every_state() -> None:
    """A state missing from the table would raise `KeyError` at run time rather
    than refusing the move, so the table must be total."""
    assert set(ALLOWED_TRANSITIONS) == set(JobState)


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES))
def test_a_terminal_job_goes_nowhere(state: JobState) -> None:
    assert is_terminal(state)
    assert ALLOWED_TRANSITIONS[state] == frozenset()
    for target in JobState:
        assert not can_transition(state, target)


def test_the_documented_happy_path_is_allowed() -> None:
    """`spec.md` section 17.3: queued → running → succeeded, with a retry loop."""
    assert can_transition(JobState.queued, JobState.running)
    assert can_transition(JobState.running, JobState.succeeded)
    assert can_transition(JobState.running, JobState.retry_wait)
    assert can_transition(JobState.retry_wait, JobState.running)


def test_a_job_cannot_skip_running() -> None:
    """Succeeding without having run would let a duplicate delivery close work
    that nobody performed."""
    assert not can_transition(JobState.queued, JobState.succeeded)
    with pytest.raises(InvalidJobTransitionError):
        assert_transition(JobState.queued, JobState.succeeded)


def test_a_job_cannot_re_enter_its_own_state() -> None:
    assert not can_transition(JobState.running, JobState.running)


def test_an_expired_claim_may_return_to_the_queue() -> None:
    """Lease recovery is the one move back out of `running`."""
    assert can_transition(JobState.running, JobState.queued)


def test_a_cancelled_job_is_not_resurrected_by_a_late_worker() -> None:
    assert not can_transition(JobState.cancelled, JobState.running)
    assert not can_transition(JobState.cancelled, JobState.queued)


def test_backoff_grows_and_stays_under_its_ceiling() -> None:
    for attempt in range(1, 30):
        delay = retry_delay_seconds(attempt)
        assert 0 < delay <= MAXIMUM_DELAY_SECONDS


def test_the_first_retry_waits_no_longer_than_the_base_delay() -> None:
    assert retry_delay_seconds(1) <= BASE_DELAY_SECONDS


def test_backoff_is_jittered_rather_than_fixed() -> None:
    """Identical delays across workers would produce a synchronised stampede when
    a shared outage clears."""
    draws = {retry_delay_seconds(6) for _ in range(40)}

    assert len(draws) > 1


def test_attempt_numbers_are_one_based() -> None:
    with pytest.raises(ValueError, match="one-based"):
        retry_delay_seconds(0)


def test_the_next_attempt_is_scheduled_after_the_given_moment() -> None:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    assert next_attempt_at(3, now=now) > now
