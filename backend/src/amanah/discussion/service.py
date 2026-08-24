"""Creating snapshots, notes, captures, reactions, and retractions (B-S27.3 to B-S27.6).

Every rule ADR 0004 records is implemented as a refusal somewhere in this file,
and where the database can hold the rule instead, it does.

*A snapshot freezes.* The counts arrive with the claim and are written once; the
table's trigger refuses an update afterwards. What a later reader checks is the
same numerator and denominator the author was looking at.

*Participation is invited.* Posting, capturing, and reacting all require a live
`discussion_participants` row. Reading does not: a colleague may follow a thread
before they can add to it, which is the difference between a closed conversation
and a private one.

*Retraction preserves the row.* The body is replaced with a fixed notice and the
capture is detached. The post keeps its author, its timestamp, and its place in
the thread, so a reader can see that a turn was taken and withdrawn rather than
finding a silent gap.

*Reactions do not rank people.* One row per person per post, counted per post.
Nothing in this module or in the projections behind it aggregates by author.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.contributions.rate_limit import (
    DISCUSSION_POST_LIMIT,
    SNAPSHOT_INSIGHT_LIMIT,
    enforce,
)
from amanah.db.models.discussion import (
    DashboardCapture,
    DiscussionParticipant,
    DiscussionPost,
    PostReaction,
    SnapshotInsight,
)
from amanah.domain.enums import ReactionKind

logger = logging.getLogger(__name__)

#: What a retracted note reads as. Fixed text rather than an empty body, so the
#: thread says what happened instead of showing a blank turn.
RETRACTED_BODY = "This note was retracted by its author."


class ParticipationRequiredError(PermissionError):
    """The caller has not been invited to take part (ADR 0004)."""


class DiscussionRejectedError(ValueError):
    """The request cannot be carried out as asked."""

    def __init__(self, message: str, *, is_conflict: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.is_conflict = is_conflict


@dataclass(frozen=True, slots=True)
class SnapshotRequest:
    """A figure a viewer chose to freeze, with the counts it already carried."""

    title: str
    claim: str
    metric: str
    numerator: int
    denominator: int
    window_start: datetime
    window_end: datetime
    figure_label: str
    filter_hash: str
    explorer_href: str
    source_keys: tuple[str, ...]
    items_observed: int
    items_relevant: int


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    """A first-party capture of an Amanah figure."""

    alt_text: str
    image_source: str
    filter_hash: str
    explorer_href: str


class DiscussionService:
    """Owns writes to snapshots, captures, notes, and reactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # -- participation ----------------------------------------------------

    def may_participate(self, user_id: UUID) -> bool:
        """Whether this person currently holds an invitation."""
        return (
            self._session.execute(
                select(DiscussionParticipant.id).where(
                    DiscussionParticipant.user_id == user_id,
                    DiscussionParticipant.revoked_at.is_(None),
                )
            ).scalar_one_or_none()
            is not None
        )

    def invite(self, *, user_id: UUID, granted_by: UUID) -> None:
        """Grant participation. Re-inviting somebody who already has it is a no-op."""
        self._session.execute(
            insert(DiscussionParticipant)
            .values(user_id=user_id, granted_by=granted_by)
            .on_conflict_do_nothing(
                index_elements=[DiscussionParticipant.user_id],
                # The unique index only covers live invitations, so the
                # inference has to name the same predicate.
                index_where=text("revoked_at IS NULL"),
            )
        )
        self._session.commit()
        logger.info("discussion participation granted", extra={"user_id": str(user_id)})

    def _require_participation(self, user_id: UUID) -> None:
        if not self.may_participate(user_id):
            logger.info("discussion write refused: not invited", extra={"user_id": str(user_id)})
            raise ParticipationRequiredError

    # -- snapshots --------------------------------------------------------

    def create_snapshot(self, *, user_id: UUID, request: SnapshotRequest) -> SnapshotInsight:
        """Freeze one figure. Creating is an authenticated action (ADR 0004).

        Anyone signed in may start a snapshot: it records a number the dashboard
        already showed them, which is not the same act as adding to a thread.
        That also makes it the one write here an invitation does not bound, so it
        carries its own limit.
        """
        enforce(
            self._session,
            SNAPSHOT_INSIGHT_LIMIT,
            user_id=user_id,
            owner_column=SnapshotInsight.user_id,
            created_column=SnapshotInsight.created_at,
        )
        insight = SnapshotInsight(
            user_id=user_id,
            title=request.title,
            claim=request.claim,
            metric=request.metric,
            numerator=request.numerator,
            denominator=request.denominator,
            window_start=request.window_start,
            window_end=request.window_end,
            figure_label=request.figure_label,
            filter_hash=request.filter_hash,
            explorer_href=request.explorer_href,
            source_keys=list(request.source_keys),
            items_observed=request.items_observed,
            items_relevant=request.items_relevant,
        )
        self._session.add(insight)
        self._session.commit()
        logger.info("snapshot insight created", extra={"insight_id": str(insight.id)})
        return insight

    # -- captures ---------------------------------------------------------

    def create_capture(self, *, user_id: UUID, request: CaptureRequest) -> DashboardCapture:
        """Store a first-party figure capture.

        `image_source` and `explorer_href` are both required to be relative, and
        the database enforces it. An absolute URL would mean the capture points
        at somebody else's server, which is exactly the screenshot board ADR 0004
        refused.
        """
        self._require_participation(user_id)
        capture = DashboardCapture(
            user_id=user_id,
            alt_text=request.alt_text,
            image_source=request.image_source,
            filter_hash=request.filter_hash,
            explorer_href=request.explorer_href,
        )
        self._session.add(capture)
        self._session.commit()
        logger.info("dashboard capture stored", extra={"capture_id": str(capture.id)})
        return capture

    # -- notes ------------------------------------------------------------

    def add_post(
        self,
        *,
        user_id: UUID,
        snapshot_insight_id: UUID,
        body: str,
        dashboard_capture_id: UUID | None = None,
    ) -> DiscussionPost:
        """Add one note to one insight."""
        self._require_participation(user_id)
        if self._session.get(SnapshotInsight, snapshot_insight_id) is None:
            raise DiscussionRejectedError("That insight was not found.")
        if dashboard_capture_id is not None:
            capture = self._session.get(DashboardCapture, dashboard_capture_id)
            if capture is None or capture.user_id != user_id:
                # Attaching somebody else's capture would let a note borrow a
                # figure its author never saw the filters for.
                raise DiscussionRejectedError("That capture was not found.")

        enforce(
            self._session,
            DISCUSSION_POST_LIMIT,
            user_id=user_id,
            owner_column=DiscussionPost.user_id,
            created_column=DiscussionPost.created_at,
        )

        post = DiscussionPost(
            snapshot_insight_id=snapshot_insight_id,
            user_id=user_id,
            body=body,
            dashboard_capture_id=dashboard_capture_id,
        )
        self._session.add(post)
        self._session.commit()
        logger.info(
            "discussion note added",
            extra={"post_id": str(post.id), "insight_id": str(snapshot_insight_id)},
        )
        return post

    def retract(self, post_id: UUID, *, user_id: UUID) -> DiscussionPost:
        """Withdraw one's own note, leaving the row (ADR 0004).

        Retracting twice is idempotent: the second call finds the notice already
        in place and returns the same row rather than stamping a new timestamp
        over the moment the author actually withdrew it.
        """
        post = self._session.get(DiscussionPost, post_id)
        if post is None or post.user_id != user_id:
            raise DiscussionRejectedError("That note was not found.")
        if post.retracted_at is not None:
            return post

        post.body = RETRACTED_BODY
        post.dashboard_capture_id = None
        post.retracted_at = datetime.now(UTC)
        self._session.commit()
        logger.info("discussion note retracted", extra={"post_id": str(post.id)})
        return post

    # -- reactions --------------------------------------------------------

    def react(self, post_id: UUID, *, user_id: UUID, kind: ReactionKind) -> None:
        """Record this person's single reaction to one post.

        Reacting again replaces their own reaction rather than adding a second,
        which is what makes the endpoint idempotent and keeps the per-post counts
        a count of people rather than of clicks.
        """
        self._require_participation(user_id)
        post = self._session.get(DiscussionPost, post_id)
        if post is None:
            raise DiscussionRejectedError("That note was not found.")
        if post.retracted_at is not None:
            raise DiscussionRejectedError("A retracted note cannot be reacted to.")

        self._session.execute(
            insert(PostReaction)
            .values(discussion_post_id=post_id, user_id=user_id, kind=kind)
            .on_conflict_do_update(
                constraint="post_reactions_discussion_post_id_user_id_unique",
                set_={"kind": kind},
            )
        )
        self._session.commit()
        logger.info("reaction recorded", extra={"post_id": str(post_id), "kind": kind.value})
