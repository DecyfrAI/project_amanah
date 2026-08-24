"""Appending user-safe lines to a contribution timeline (B-S16.4, B-S17.6).

A timeline is history, not a status summary. Every transition appends a row and
nothing here ever updates or deletes one, so a user reading "Your Contributions"
sees what actually happened rather than a state machine's current opinion of it.

Two properties matter and both are enforced rather than intended. The message is
**user-safe**: it is composed here from controlled vocabulary, never from a
provider response, a reviewer's private note, or the source text. And appending
is **idempotent**: a redelivered transition collides with the unique constraint
on `(contribution_id, event_type, public_message)` and is absorbed, so a retried
job cannot write the same line twice.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.community import ContributionEvent
from amanah.domain.enums import ContributionEventType, ContributionType

logger = logging.getLogger(__name__)


class ContributionTimeline:
    """Appends what happened to one user's contribution."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        *,
        user_id: UUID,
        contribution_type: ContributionType,
        contribution_id: UUID,
        event_type: ContributionEventType,
        public_message: str,
    ) -> None:
        """Add one line, or absorb it if the identical line is already there.

        The caller does not need to know whether this is a first delivery or a
        retry: both leave the timeline reading correctly, which is the whole
        point of making the append idempotent rather than conditional.
        """
        self._session.execute(
            insert(ContributionEvent)
            .values(
                user_id=user_id,
                contribution_type=contribution_type,
                contribution_id=contribution_id,
                event_type=event_type,
                public_message=public_message,
            )
            .on_conflict_do_nothing(
                constraint="contribution_events_contribution_event_message_unique"
            )
        )
        logger.info(
            "contribution event appended",
            extra={
                "contribution_type": contribution_type.value,
                "contribution_id": str(contribution_id),
                "event_type": event_type.value,
            },
        )
