"""Human-governed lifecycle for the curated external resource catalog."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from amanah.api.schemas.resources import CreateResourceRequest, UpdateResourceRequest
from amanah.db.repositories.resource_governance import (
    ResourceGovernanceRepository,
    ResourceUrlPersistenceConflictError,
)
from amanah.domain.enums import PublicationStatus

logger = logging.getLogger(__name__)


class ResourceGovernanceError(ValueError):
    """A safe, expected catalog-governance failure."""


class ResourceMissingError(ResourceGovernanceError):
    """The requested managed resource is not visible."""


class ResourceUrlConflictError(ResourceGovernanceError):
    """Another catalog entry already owns the URL."""


class ResourceLifecycleError(ResourceGovernanceError):
    """The requested lifecycle transition is not permitted."""


class ResourceGovernanceService:
    """Create drafts and require an explicit human action to publish them."""

    def __init__(self, repository: ResourceGovernanceRepository) -> None:
        self._repository = repository

    def create(self, request: CreateResourceRequest, actor_user_id: UUID) -> Row[Any]:
        self._ensure_url_available(request.url)
        values = request.model_dump(mode="python")
        values["status"] = PublicationStatus.draft
        try:
            resource_id = self._repository.create_resource(values)
        except ResourceUrlPersistenceConflictError as exc:
            raise ResourceUrlConflictError("A resource with this URL already exists.") from exc
        self._repository.flush()
        row = self._require_resource(resource_id)
        self._audit(row, actor_user_id, "created")
        self._repository.commit()
        logger.info(
            "resource governance action completed",
            extra={
                "resource_id": str(resource_id),
                "actor_user_id": str(actor_user_id),
                "action": "created",
            },
        )
        return self._require_resource(resource_id)

    def update(
        self, resource_id: UUID, request: UpdateResourceRequest, actor_user_id: UUID
    ) -> Row[Any]:
        current = self._require_resource(resource_id)
        changes = request.model_dump(mode="python", exclude_unset=True)
        requested_url = changes.get("url")
        if isinstance(requested_url, str) and requested_url != current.url:
            self._ensure_url_available(requested_url)

        if current.status == PublicationStatus.published.value:
            # Any wording/link change invalidates the previous review. The entry
            # becomes a draft and requires a fresh explicit publish action.
            changes.update(
                status=PublicationStatus.draft,
                reviewed_by=None,
                last_reviewed_at=None,
            )
        changes["updated_at"] = datetime.now(UTC)
        try:
            self._repository.update_resource(resource_id, changes)
        except ResourceUrlPersistenceConflictError as exc:
            raise ResourceUrlConflictError("A resource with this URL already exists.") from exc
        self._repository.flush()
        row = self._require_resource(resource_id)
        self._audit(row, actor_user_id, "updated")
        self._repository.commit()
        logger.info(
            "resource governance action completed",
            extra={
                "resource_id": str(resource_id),
                "actor_user_id": str(actor_user_id),
                "action": "updated",
            },
        )
        return self._require_resource(resource_id)

    def publish(self, resource_id: UUID, actor_user_id: UUID) -> Row[Any]:
        current = self._require_resource(resource_id)
        if current.status == PublicationStatus.published.value:
            raise ResourceLifecycleError("This resource is already published.")
        moment = datetime.now(UTC)
        self._repository.update_resource(
            resource_id,
            {
                "status": PublicationStatus.published,
                "reviewed_by": str(actor_user_id),
                "last_reviewed_at": moment,
                "updated_at": moment,
            },
        )
        self._repository.flush()
        row = self._require_resource(resource_id)
        self._audit(row, actor_user_id, "published")
        self._repository.commit()
        logger.info(
            "resource governance action completed",
            extra={
                "resource_id": str(resource_id),
                "actor_user_id": str(actor_user_id),
                "action": "published",
            },
        )
        return self._require_resource(resource_id)

    def archive(self, resource_id: UUID, actor_user_id: UUID) -> Row[Any]:
        current = self._require_resource(resource_id)
        if current.status == PublicationStatus.archived.value:
            raise ResourceLifecycleError("This resource is already archived.")
        self._repository.update_resource(
            resource_id,
            {"status": PublicationStatus.archived, "updated_at": datetime.now(UTC)},
        )
        self._repository.flush()
        row = self._require_resource(resource_id)
        self._audit(row, actor_user_id, "archived")
        self._repository.commit()
        logger.info(
            "resource governance action completed",
            extra={
                "resource_id": str(resource_id),
                "actor_user_id": str(actor_user_id),
                "action": "archived",
            },
        )
        return self._require_resource(resource_id)

    def _require_resource(self, resource_id: UUID) -> Row[Any]:
        row = self._repository.get_resource(resource_id)
        if row is None:
            raise ResourceMissingError("This resource was not found.")
        return row

    def _ensure_url_available(self, url: str) -> None:
        if self._repository.find_by_url(url) is not None:
            raise ResourceUrlConflictError("A resource with this URL already exists.")

    def _audit(self, row: Row[Any], actor_user_id: UUID, action: str) -> None:
        snapshot: dict[str, object] = {
            "title": row.title,
            "organization": row.organization,
            "url": row.url,
            "country_scope": row.country_scope,
            "category": row.category,
            "summary": row.summary,
            "status": row.status,
            "reviewed_by": row.reviewed_by,
            "last_reviewed_at": (
                row.last_reviewed_at.isoformat() if row.last_reviewed_at else None
            ),
        }
        self._repository.add_audit_event(
            resource_id=UUID(str(row.id)),
            actor_user_id=actor_user_id,
            action=action,
            snapshot=snapshot,
        )
