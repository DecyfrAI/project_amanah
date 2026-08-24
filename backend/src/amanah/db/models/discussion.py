"""Snapshot insights and the invite-only discussion attached to them (ADR 0004).

ADR 0004 refused a public forum, and the shape here is what that refusal looks
like in a schema. There is no thread table with no parent: a note hangs off a
`snapshot_insights` row or it does not exist. There is no reputation column, no
score, and no per-author aggregate — a reaction counts on a post and stops there.
Retraction replaces a body and drops the capture while the row stays, so a thread
never silently loses a turn it actually had.

`insight_snapshots` in `metrics.py` is a different thing with a confusingly close
name: that is the cache of a generated narrative, keyed by filter and model
version. A `snapshot_insight` here is a person freezing a figure they were
looking at, and it carries no model output at all.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from amanah.db.base import Base, CreatedAt, Timestamp, UuidColumn, UuidPrimaryKey
from amanah.db.enums import enum_column
from amanah.domain.enums import ReactionKind

#: Longest note the discussion accepts. Long enough for a paragraph of context,
#: short enough that a post stays a note rather than an essay nobody reads.
MAXIMUM_POST_LENGTH = 4000

#: Longest claim a snapshot may freeze. The claim is the sentence the figure
#: already states, so it does not need room for an argument.
MAXIMUM_CLAIM_LENGTH = 500


class DiscussionParticipant(Base):
    """One person invited to take part in discussion (ADR 0004).

    Participation is invite-only, so posting and reacting check for a live row
    here. Reading is not gated by it: an authenticated colleague may follow a
    thread without being able to add to it. Revocation sets `revoked_at` rather
    than deleting the row, so who was invited when stays answerable.
    """

    __tablename__ = "discussion_participants"
    __table_args__ = (
        Index(
            "discussion_participants_user_id_idx",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name="revocation_after_grant",
        ),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    granted_by: Mapped[UuidColumn] = mapped_column(
        nullable=False, doc="The reviewer or administrator who issued the invitation."
    )
    granted_at: Mapped[CreatedAt]
    revoked_at: Mapped[Timestamp | None]


class DashboardCapture(Base):
    """A first-party capture of an Amanah figure (ADR 0004).

    Only figures this product rendered. `image_source` names a first-party
    rendering, never an uploaded screenshot of someone else's platform: ADR 0004
    refused a screenshot board precisely because it would redistribute harmful
    material. The filter hash and the Explorer link are what make the capture
    checkable — a reader can reopen the exact filter state it came from.
    """

    __tablename__ = "dashboard_captures"
    __table_args__ = (
        CheckConstraint("length(alt_text) BETWEEN 1 AND 300", name="alt_text_length"),
        # A first-party rendering, addressed inside this product. An absolute URL
        # here would mean the capture points at somebody else's server, and
        # `//host/path` is one of those however much it looks like a path.
        CheckConstraint(
            "explorer_href LIKE '/%' AND explorer_href NOT LIKE '//%'",
            name="explorer_href_is_relative",
        ),
        CheckConstraint(
            "image_source LIKE '/%' AND image_source NOT LIKE '//%'",
            name="image_source_is_first_party",
        ),
        Index("dashboard_captures_user_id_created_at_idx", "user_id", text("created_at DESC")),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    alt_text: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Required: a figure with no alt text is unusable to a reader."
    )
    image_source: Mapped[str] = mapped_column(
        Text, nullable=False, doc="First-party path of the rendered figure."
    )
    filter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    explorer_href: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Relative Explorer deep link reproducing the capture's filters."
    )
    created_at: Mapped[CreatedAt]


class SnapshotInsight(Base):
    """A figure a signed-in viewer froze, with the counts that produced it.

    Immutable after creation, enforced by a trigger in the migration. The point
    of a snapshot is that a later reader can check the claim against the same
    numbers the author saw, which a row that could be edited afterwards would not
    support. The denominator travels with the numerator for the same reason every
    rate in this product does.
    """

    __tablename__ = "snapshot_insights"
    __table_args__ = (
        CheckConstraint("numerator >= 0 AND denominator >= 0", name="counts_non_negative"),
        CheckConstraint("numerator <= denominator", name="numerator_within_denominator"),
        CheckConstraint(
            "items_relevant >= 0 AND items_observed >= items_relevant",
            name="observed_covers_relevant",
        ),
        CheckConstraint("window_end >= window_start", name="window_ordered"),
        CheckConstraint(f"length(claim) BETWEEN 1 AND {MAXIMUM_CLAIM_LENGTH}", name="claim_length"),
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint(
            "explorer_href LIKE '/%' AND explorer_href NOT LIKE '//%'",
            name="explorer_href_is_relative",
        ),
        Index("snapshot_insights_created_at_idx", text("created_at DESC")),
        Index("snapshot_insights_user_id_created_at_idx", "user_id", text("created_at DESC")),
    )

    id: Mapped[UuidPrimaryKey]
    user_id: Mapped[UuidColumn] = mapped_column(
        nullable=False, doc="Who froze the figure. Creating is an authenticated action."
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[str] = mapped_column(
        Text, nullable=False, doc="The sentence the figure already states, not a new assertion."
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    numerator: Mapped[int] = mapped_column(Integer, nullable=False)
    denominator: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[Timestamp] = mapped_column(nullable=False)
    window_end: Mapped[Timestamp] = mapped_column(nullable=False)
    figure_label: Mapped[str] = mapped_column(Text, nullable=False)
    filter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    explorer_href: Mapped[str] = mapped_column(
        Text, nullable=False, doc="The filter state at capture time, not a live query."
    )
    source_keys: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
        doc="Sources the denominator was drawn from, frozen with the counts.",
    )
    items_observed: Mapped[int] = mapped_column(Integer, nullable=False)
    items_relevant: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[CreatedAt]


class DiscussionPost(Base):
    """One note on one snapshot insight.

    A post always has a parent insight; there is no free-floating board. A
    retracted post keeps its row, its author, and its position in the thread, and
    loses its body and its capture.
    """

    __tablename__ = "discussion_posts"
    __table_args__ = (
        CheckConstraint(
            f"length(body) BETWEEN 1 AND {MAXIMUM_POST_LENGTH}",
            name="body_length",
        ),
        # Retraction is what removes the capture, so the two can never disagree.
        CheckConstraint(
            "retracted_at IS NULL OR dashboard_capture_id IS NULL",
            name="retracted_post_has_no_capture",
        ),
        CheckConstraint(
            "retracted_at IS NULL OR retracted_at >= created_at",
            name="retraction_after_creation",
        ),
        Index(
            "discussion_posts_snapshot_insight_id_created_at_idx",
            "snapshot_insight_id",
            "created_at",
        ),
        Index("discussion_posts_user_id_created_at_idx", "user_id", text("created_at DESC")),
        Index("discussion_posts_dashboard_capture_id_idx", "dashboard_capture_id"),
    )

    id: Mapped[UuidPrimaryKey]
    snapshot_insight_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("snapshot_insights.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    dashboard_capture_id: Mapped[UuidColumn | None] = mapped_column(
        ForeignKey("dashboard_captures.id", ondelete="SET NULL")
    )
    created_at: Mapped[CreatedAt]
    retracted_at: Mapped[Timestamp | None]

    snapshot_insight: Mapped[SnapshotInsight] = relationship()
    dashboard_capture: Mapped[DashboardCapture | None] = relationship()


class PostReaction(Base):
    """One person's reaction to one post.

    One row per person per post, so reacting twice is idempotent and a reaction
    cannot be stacked. Nothing aggregates these by author: the only sum the
    product computes is per post, which is what keeps this a signal about a note
    rather than a score for a person.
    """

    __tablename__ = "post_reactions"
    __table_args__ = (
        UniqueConstraint(
            "discussion_post_id",
            "user_id",
            name="post_reactions_discussion_post_id_user_id_unique",
        ),
        Index("post_reactions_discussion_post_id_idx", "discussion_post_id"),
        Index("post_reactions_user_id_idx", "user_id"),
    )

    id: Mapped[UuidPrimaryKey]
    discussion_post_id: Mapped[UuidColumn] = mapped_column(
        ForeignKey("discussion_posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UuidColumn] = mapped_column(nullable=False)
    kind: Mapped[ReactionKind] = mapped_column(enum_column(ReactionKind), nullable=False)
    created_at: Mapped[CreatedAt]

    discussion_post: Mapped[DiscussionPost] = relationship()
