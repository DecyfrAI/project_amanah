"""Per-user action limits for the AI surfaces (B-S25.6).

A fixed-window counter, in process memory. That is the honest scope: it protects
one API process's Gemini budget from one signed-in person in a loop, and it makes
no claim to be a distributed limiter. B-S22.4 adds the shared, `Retry-After`-aware
limiter across every endpoint; this is the narrower guard the assistant needs now,
because that endpoint is the one place a user can spend model tokens directly.

Windows are fixed rather than sliding. A sliding window would need per-request
timestamps retained per user, which is more state than a spend guard justifies —
and the failure mode of a fixed window (a burst across a boundary) costs at most
one extra window of calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

#: The assistant's default allowance. Generous enough for real exploration of a
#: dashboard, tight enough that a loop cannot drain a day's token budget.
ASSISTANT_REQUESTS_PER_WINDOW = 20
ASSISTANT_WINDOW = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Whether the action may proceed, and when to try again if not."""

    is_allowed: bool
    retry_after_seconds: int = 0


class FixedWindowRateLimiter:
    """Counts one user's actions inside a fixed window."""

    def __init__(self, *, limit: int, window: timedelta) -> None:
        self._limit = limit
        self._window = window
        self._counts: dict[UUID, tuple[datetime, int]] = {}

    def check(self, user_id: UUID, *, now: datetime | None = None) -> RateLimitDecision:
        """Record an attempt and say whether it is permitted.

        The attempt is counted whether or not it is allowed to proceed, so a
        client that ignores the refusal does not get a fresh allowance by
        retrying inside the same window.
        """
        moment = now or datetime.now(UTC)
        window_start, count = self._counts.get(user_id, (moment, 0))
        if moment - window_start >= self._window:
            window_start, count = moment, 0

        count += 1
        self._counts[user_id] = (window_start, count)
        if count > self._limit:
            remaining = self._window - (moment - window_start)
            return RateLimitDecision(
                is_allowed=False,
                retry_after_seconds=max(1, int(remaining.total_seconds())),
            )
        return RateLimitDecision(is_allowed=True)
