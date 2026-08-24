"""Per-run and daily token budgets (B-S13.5).

`spec.md` section 11.2 requires both, and requires that exhausting one defers the
remaining items rather than failing the run. The tracker therefore answers two
different questions: *may I spend?* before a call, and *what did that cost?*
after one.

Reservation happens before the request because the cost of a call is not known
until it returns, and a budget checked only afterwards has already been exceeded.
The estimate is charged up front and reconciled against the provider's reported
usage once the answer arrives, so a run cannot overshoot by more than one call's
estimate even if every estimate is wrong.

The daily window rolls on UTC calendar date. That is a deliberate simplification
over a sliding window: a Flash-class budget is an operating-cost guard, and an
operator reading a run summary can reason about "today" without also reasoning
about when a 24-hour window happened to start.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

#: Characters per token, used to estimate a request's cost before sending it.
#: Deliberately pessimistic against typical English so the estimate over-reserves
#: rather than under-reserves; the reconciliation after the call gives the budget
#: back the difference.
_CHARACTERS_PER_TOKEN = 3.0


def estimate_tokens(text: str) -> int:
    """A conservative token estimate for text about to be sent.

    An estimate rather than a real tokenizer count: importing the provider's
    tokenizer to guard a cost ceiling would add a dependency whose only job is to
    make a safety margin slightly narrower.
    """
    return max(1, int(len(text) / _CHARACTERS_PER_TOKEN) + 1)


@dataclass(frozen=True, slots=True)
class BudgetGrant:
    """The answer to "may I spend?".

    `reason` is set only when refused, and is a stable code because it is stored
    on a deferred prediction and surfaced in a redacted run summary.
    """

    is_granted: bool
    reason: str | None = None


class TokenBudget:
    """Tracks token spend against a per-run and a daily ceiling.

    One instance per run. It is not thread-safe and is not shared between
    processes: two concurrent ETL runs each get their own run ceiling, and the
    daily ceiling they share is enforced per process. `spec.md` prevents
    overlapping production ETL runs (B-S21.6), so that is the real deployment
    shape rather than an assumption this class invents.
    """

    def __init__(
        self,
        *,
        per_run_tokens: int,
        daily_tokens: int,
        today: date | None = None,
    ) -> None:
        self._per_run_tokens = per_run_tokens
        self._daily_tokens = daily_tokens
        self._run_spent = 0
        self._daily_spent = 0
        self._day = today or datetime.now(UTC).date()

    @property
    def run_spent_tokens(self) -> int:
        return self._run_spent

    @property
    def daily_spent_tokens(self) -> int:
        return self._daily_spent

    def request(self, estimated_tokens: int, *, now: datetime | None = None) -> BudgetGrant:
        """Reserve an estimated cost, or refuse with a stable reason."""
        self._roll_day(now)
        if self._run_spent + estimated_tokens > self._per_run_tokens:
            return BudgetGrant(is_granted=False, reason="run_token_budget_exhausted")
        if self._daily_spent + estimated_tokens > self._daily_tokens:
            return BudgetGrant(is_granted=False, reason="daily_token_budget_exhausted")
        self._run_spent += estimated_tokens
        self._daily_spent += estimated_tokens
        return BudgetGrant(is_granted=True)

    def reconcile(self, *, estimated_tokens: int, actual_tokens: int) -> None:
        """Replace a reservation with what the call actually cost.

        Clamped at zero so a provider that reports no usage cannot credit the
        budget below what has genuinely been spent.
        """
        adjustment = actual_tokens - estimated_tokens
        self._run_spent = max(0, self._run_spent + adjustment)
        self._daily_spent = max(0, self._daily_spent + adjustment)

    def release(self, estimated_tokens: int) -> None:
        """Return a reservation for a call that never reached the provider.

        A request refused by the policy gate or served from cache spends nothing,
        and holding its reservation would shrink the run's budget for no reason.
        """
        self.reconcile(estimated_tokens=estimated_tokens, actual_tokens=0)

    def _roll_day(self, now: datetime | None) -> None:
        today = (now or datetime.now(UTC)).astimezone(UTC).date()
        if today != self._day:
            self._day = today
            self._daily_spent = 0
