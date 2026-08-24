"""Reviewer/admin governance routes for the curated resource catalog."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from sqlalchemy import Row
from sqlalchemy.orm import Session

from amanah.api.dependencies import (
    DatabaseSession,
    build_response_meta,
    get_settings,
    require_reviewer,
)
from amanah.api.errors import ApiError, ConflictError, ResourceNotFoundError
from amanah.api.schemas.resources import (
    CreateResourceRequest,
    ManagedResourceEntry,
    ManagedResourceListResponse,
    ManagedResourceResponse,
    PublishResourceRequest,
    ResourceAuditEvent,
    ResourceAuditResponse,
    UpdateResourceRequest,
)
from amanah.auth.principal import AuthenticatedUser
from amanah.db.repositories.resource_governance import ResourceGovernanceRepository
from amanah.domain.enums import PublicationStatus
from amanah.resources.governance import (
    ResourceGovernanceService,
    ResourceLifecycleError,
    ResourceMissingError,
    ResourceUrlConflictError,
)
from amanah.settings import Settings

router = APIRouter(
    prefix="/admin/resources",
    tags=["resource administration"],
    dependencies=[Depends(require_reviewer)],
)


def _entry(row: Row[Any]) -> ManagedResourceEntry:
    return ManagedResourceEntry(
        id=row.id,
        title=row.title,
        organization=row.organization,
        url=row.url,
        country_scope=row.country_scope,
        category=row.category,
        summary=row.summary,
        status=row.status,
        last_reviewed_at=row.last_reviewed_at,
        reviewed_by=row.reviewed_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _audit_event(row: Row[Any]) -> ResourceAuditEvent:
    return ResourceAuditEvent(
        id=row.id,
        resource_entry_id=row.resource_entry_id,
        actor_user_id=row.actor_user_id,
        action=row.action,
        snapshot=row.snapshot,
        created_at=row.created_at,
    )


def _service(session: Session) -> ResourceGovernanceService:
    return ResourceGovernanceService(ResourceGovernanceRepository(session))


def _governance_error(exc: Exception) -> ApiError:
    if isinstance(exc, ResourceMissingError):
        return ResourceNotFoundError("This resource was not found.")
    if isinstance(exc, (ResourceUrlConflictError, ResourceLifecycleError)):
        return ConflictError(str(exc))
    raise exc


@router.get("", summary="List managed resource entries")
def list_resources(
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    status: PublicationStatus | None = None,
) -> ManagedResourceListResponse:
    rows = ResourceGovernanceRepository(session).list_resources(status=status)
    return ManagedResourceListResponse(
        resources=[_entry(row) for row in rows], meta=build_response_meta(settings)
    )


@router.post(
    "",
    summary="Create a draft resource entry",
    status_code=http_status.HTTP_201_CREATED,
)
def create_resource(
    request: CreateResourceRequest,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
) -> ManagedResourceResponse:
    try:
        row = _service(session).create(request, reviewer.user_id)
    except (ResourceMissingError, ResourceUrlConflictError, ResourceLifecycleError) as exc:
        raise _governance_error(exc) from exc
    return ManagedResourceResponse(resource=_entry(row), meta=build_response_meta(settings))


@router.get("/{resource_id}", summary="Read a managed resource entry")
def read_resource(
    resource_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ManagedResourceResponse:
    row = ResourceGovernanceRepository(session).get_resource(resource_id)
    if row is None:
        raise ResourceNotFoundError("This resource was not found.")
    return ManagedResourceResponse(resource=_entry(row), meta=build_response_meta(settings))


@router.patch("/{resource_id}", summary="Update curated resource fields")
def update_resource(
    resource_id: UUID,
    request: UpdateResourceRequest,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
) -> ManagedResourceResponse:
    try:
        row = _service(session).update(resource_id, request, reviewer.user_id)
    except (ResourceMissingError, ResourceUrlConflictError, ResourceLifecycleError) as exc:
        raise _governance_error(exc) from exc
    return ManagedResourceResponse(resource=_entry(row), meta=build_response_meta(settings))


@router.post("/{resource_id}/publish", summary="Publish a reviewed resource entry")
def publish_resource(
    resource_id: UUID,
    request: PublishResourceRequest,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
) -> ManagedResourceResponse:
    del request  # Parsing it is the explicit reviewed-summary confirmation.
    try:
        row = _service(session).publish(resource_id, reviewer.user_id)
    except (ResourceMissingError, ResourceUrlConflictError, ResourceLifecycleError) as exc:
        raise _governance_error(exc) from exc
    return ManagedResourceResponse(resource=_entry(row), meta=build_response_meta(settings))


@router.post("/{resource_id}/archive", summary="Archive a resource entry")
def archive_resource(
    resource_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
    reviewer: Annotated[AuthenticatedUser, Depends(require_reviewer)],
) -> ManagedResourceResponse:
    try:
        row = _service(session).archive(resource_id, reviewer.user_id)
    except (ResourceMissingError, ResourceUrlConflictError, ResourceLifecycleError) as exc:
        raise _governance_error(exc) from exc
    return ManagedResourceResponse(resource=_entry(row), meta=build_response_meta(settings))


@router.get("/{resource_id}/audit", summary="Read append-only resource audit history")
def read_resource_audit(
    resource_id: UUID,
    session: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ResourceAuditResponse:
    repository = ResourceGovernanceRepository(session)
    if repository.get_resource(resource_id) is None:
        raise ResourceNotFoundError("This resource was not found.")
    return ResourceAuditResponse(
        events=[_audit_event(row) for row in repository.list_audit_events(resource_id)],
        meta=build_response_meta(settings),
    )
