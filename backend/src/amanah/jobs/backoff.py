"""Bounded exponential backoff with jitter for retryable failures.

Two properties matter and they pull against each other. The delay must grow, so
a struggling provider is not hammered; and the delays of many workers must not
coincide, so a shared outage does not produce a synchronised retry stampede when
it clears. Full jitter gives both: the ceiling doubles per attempt and the actual
wait is drawn uniformly below it.

`rules/backend.md` allows this only for transient failures. A rejected URL, an
unapproved licence, or a policy block is permanent and never comes here.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

#: First ceiling, in seconds. Attempt 1 waits somewhere in (0, 2].
BASE_DELAY_SECONDS = 2.0

#: Ceiling on the ceiling: without it, attempt 12 would schedule itself days out.
MAXIMUM_DELAY_SECONDS = 900.0

#: Cap on the exponent, so a large attempt count cannot overflow the shift.
_MAXIMUM_EXPONENT = 16

#: Resolution of the jitter draw. `secrets` gives whole numbers only, so the
#: delay is drawn in milliseconds and converted.
_MILLISECONDS = 1000


def retry_delay_seconds(attempt: int) -> float:
    """Return the wait before `attempt`, drawn uniformly under a doubling ceiling.

    `attempt` is one-based: the delay before the first retry is `attempt=1`.
    """
    if attempt < 1:
        raise ValueError("attempt is one-based and must be at least 1")
    exponent = min(attempt - 1, _MAXIMUM_EXPONENT)
    ceiling = min(BASE_DELAY_SECONDS * (2**exponent), MAXIMUM_DELAY_SECONDS)
    # `secrets` rather than `random`: the module-level `random` sequence is
    # shared process state, and bandit flags it in any case. Nothing here needs
    # cryptographic strength, but nothing here is harmed by having it.
    drawn = secrets.randbelow(int(ceiling * _MILLISECONDS)) + 1
    return drawn / _MILLISECONDS


def next_attempt_at(attempt: int, *, now: datetime | None = None) -> datetime:
    """The UTC instant at which `attempt` becomes eligible."""
    moment = now if now is not None else datetime.now(UTC)
    return moment + timedelta(seconds=retry_delay_seconds(attempt))
