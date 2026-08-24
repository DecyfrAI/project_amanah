"""Reviewer/admin persistence for the curated resource catalog."""

from __future__ import annotations

from typing import Any, Never
from uuid import UUID

from sqlalchemy import Row, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from amanah.db.models.resources import ResourceAuditEvent, ResourceEntry
from amanah.db.views import authenticated_managed_resources, authenticated_resource_audit_events
from amanah.domain.enums import PublicationStatus


class ResourceUrlPersistenceConflictError(RuntimeError):
    """A concurrent write claimed the resource URL first."""


class ResourceGovernanceRepository:
    """Write catalog rows and read only through reviewer-safe projections."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_resources(self, *, status: PublicationStatus | None = None) -> tuple[Row[Any], ...]:
        table = authenticated_managed_resources
        statement = select(table)
        if status is not None:
            statement = statement.where(table.c.status == status.value)
        statement = statement.order_by(table.c.updated_at.desc(), table.c.id.desc())
        return tuple(self._session.execute(statement).all())

    def get_resource(self, resource_id: UUID) -> Row[Any] | None:
        statement = select(authenticated_managed_resources).where(
            authenticated_managed_resources.c.id == resource_id
        )
        return self._session.execute(statement).one_or_none()

    def find_by_url(self, url: str) -> Row[Any] | None:
        statement = select(authenticated_managed_resources).where(
            authenticated_managed_resources.c.url == url
        )
        return self._session.execute(statement).one_or_none()

    def create_resource(self, values: dict[str, object]) -> UUID:
        try:
            resource_id = self._session.execute(
                insert(ResourceEntry).values(**values).returning(ResourceEntry.id)
            ).scalar_one()
        except IntegrityError as exc:
            self._raise_url_conflict_or_reraise(exc)
        return UUID(str(resource_id))

    def update_resource(self, resource_id: UUID, values: dict[str, object]) -> None:
        try:
            self._session.execute(
                update(ResourceEntry).where(ResourceEntry.id == resource_id).values(**values)
            )
        except IntegrityError as exc:
            self._raise_url_conflict_or_reraise(exc)

    def add_audit_event(
        self,
        *,
        resource_id: UUID,
        actor_user_id: UUID,
        action: str,
        snapshot: dict[str, object],
    ) -> None:
        self._session.add(
            ResourceAuditEvent(
                resource_entry_id=resource_id,
                actor_user_id=actor_user_id,
                action=action,
                snapshot=snapshot,
            )
        )

    def list_audit_events(self, resource_id: UUID) -> tuple[Row[Any], ...]:
        table = authenticated_resource_audit_events
        statement = (
            select(table)
            .where(table.c.resource_entry_id == resource_id)
            .order_by(table.c.created_at.asc(), table.c.id.asc())
        )
        return tuple(self._session.execute(statement).all())

    def commit(self) -> None:
        self._session.commit()

    def flush(self) -> None:
        self._session.flush()

    def _raise_url_conflict_or_reraise(self, exc: IntegrityError) -> Never:
        self._session.rollback()
        diagnostic = getattr(exc.orig, "diag", None)
        if getattr(diagnostic, "constraint_name", None) == "resource_entries_url_unique":
            raise ResourceUrlPersistenceConflictError from exc
        raise exc
