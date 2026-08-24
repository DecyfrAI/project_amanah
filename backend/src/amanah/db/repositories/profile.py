"""The caller's own profile row, read and written (B-S27.1).

`GET /v1/me` answered from the verified token alone until now, which was correct
while there was no stored state to report. Onboarding gives it some, so the read
joins the token identity with the persisted row — and the *role* still comes from
the token, never from the row. A stale or tampered `user_profiles.role` must not
be able to grant anything, which is why the two are kept apart here rather than
merged into one source.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import Row, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.community import UserProfile
from amanah.db.views import authenticated_user_profile
from amanah.domain.enums import OnboardingStatus, Role

logger = logging.getLogger(__name__)


class ProfileRepository:
    """Reads the caller's own profile projection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> Row[Any] | None:
        """The caller's stored profile, or `None` before they have written one."""
        table = authenticated_user_profile
        return self._session.execute(select(table).where(table.c.user_id == user_id)).one_or_none()


class ProfileService:
    """Owns writes to `user_profiles`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def update(
        self,
        *,
        user_id: UUID,
        role: Role,
        display_name: str | None = None,
        onboarding_status: OnboardingStatus | None = None,
        content_safety_preferences: dict[str, Any] | None = None,
    ) -> UserProfile:
        """Create or update the caller's own profile.

        An upsert rather than a read-then-write: the first `PATCH` a person makes
        is usually the row's first existence, and requiring a separate create step
        would put a race between two onboarding tabs.

        `role` is written from the *verified token*, so the stored value tracks
        what the server already decided. Nothing accepts a role from the request
        body; a client that sent one would have it rejected as an unknown field.
        """
        values: dict[str, Any] = {"user_id": user_id, "role": role}
        if display_name is not None:
            values["display_name"] = display_name
        if onboarding_status is not None:
            values["onboarding_status"] = onboarding_status
        if content_safety_preferences is not None:
            values["content_safety_preferences"] = content_safety_preferences

        self._session.execute(
            insert(UserProfile)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[UserProfile.user_id],
                set_={key: value for key, value in values.items() if key != "user_id"},
            )
        )
        self._session.commit()
        logger.info("profile updated", extra={"user_id": str(user_id)})
        return self._session.get_one(UserProfile, user_id)
