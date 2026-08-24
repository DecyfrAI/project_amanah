"""Per-user limits on the actions a person can take (B-S16.7, B-S18.7, B-S27.6).

Counted from the rows the action already writes rather than from a separate
counter table. That is deliberate: there is one authority for "how many
submissions has this person made in the last hour", the count survives a process
restart, and two API instances cannot each allow a full quota. It costs one
indexed `COUNT` per mutating request, which every one of these paths already
pays several of.

The limits are anti-abuse floors, not throughput tuning. `spec.md` section 9.9
asks the product to discourage brigading and duplicate mass reporting, and a
person who genuinely needs to file more than these in an hour is better served
by a conversation than by a higher number.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from amanah.api.errors import RateLimitedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ActionLimit:
    """How many of one action a person may take in one rolling window."""

    action: str
    maximum: int
    window: timedelta
    message: str


#: One URL at a time, and a bounded number per hour. High enough that a
#: researcher working through a list is not obstructed; low enough that the
#: safe-retrieval path is not a free outbound request service.
SUBMISSION_LIMIT = ActionLimit(
    action="submission",
    maximum=20,
    window=timedelta(hours=1),
    message="You have submitted the maximum number of URLs for now. Try again later.",
)

#: A dispute should follow from reading an item. Twenty an hour is well past
#: attentive reading and well short of a script.
DISPUTE_LIMIT = ActionLimit(
    action="dispute",
    maximum=20,
    window=timedelta(hours=1),
    message="You have opened the maximum number of disputes for now. Try again later.",
)

#: `spec.md` FR-TOS-009. Preparing reports in volume is exactly the brigading
#: pattern the product is required to discourage, so this is the tightest limit.
PREPARED_REPORT_LIMIT = ActionLimit(
    action="prepared_report",
    maximum=10,
    window=timedelta(hours=1),
    message="You have prepared the maximum number of platform reports for now.",
)

#: Freezing a figure is open to any signed-in viewer (ADR 0004), which makes it
#: the one discussion write an invitation does not already bound. The ceiling is
#: generous — a researcher working through a breakdown may capture a dozen rows —
#: and exists so the endpoint cannot be used to write rows without limit.
SNAPSHOT_INSIGHT_LIMIT = ActionLimit(
    action="snapshot_insight",
    maximum=40,
    window=timedelta(hours=1),
    message="You have captured the maximum number of insights for now. Try again later.",
)

#: Discussion is invite-only already; this stops an invited account from
#: flooding a thread.
DISCUSSION_POST_LIMIT = ActionLimit(
    action="discussion_post",
    maximum=30,
    window=timedelta(hours=1),
    message="You have posted the maximum number of notes for now. Try again later.",
)


def enforce(
    session: Session,
    limit: ActionLimit,
    *,
    user_id: UUID,
    owner_column: InstrumentedAttribute[UUID],
    created_column: InstrumentedAttribute[datetime],
    now: datetime | None = None,
) -> None:
    """Refuse the action when the caller is already at the limit.

    Raises `RateLimitedError`, which carries the `Retry-After` the response must
    include. The wait reported is the full window: computing the exact expiry of
    the oldest row would leak how the limit is implemented without helping the
    caller, who has to wait anyway.
    """
    moment = now if now is not None else datetime.now(UTC)
    since = moment - limit.window
    statement: Select[tuple[int]] = select(func.count()).where(
        owner_column == user_id, created_column >= since
    )
    used = session.execute(statement).scalar_one()
    if used < limit.maximum:
        return

    logger.warning(
        "action refused by rate limit",
        extra={"user_id": str(user_id), "action": limit.action, "used": used},
    )
    raise RateLimitedError(
        retry_after_seconds=int(limit.window.total_seconds()),
        message=limit.message,
    )
