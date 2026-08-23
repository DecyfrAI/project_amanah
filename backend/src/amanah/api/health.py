"""Unauthenticated operational endpoints.

`/healthz` and `/readyz` are the only routes this service exposes without a
verified session. Neither returns secrets, connection strings, dependency
versions, or build identifiers.
"""

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from amanah.api.dependencies import get_settings
from amanah.api.schemas.base import ResponseModel
from amanah.db.session import Database
from amanah.settings import Settings

router = APIRouter(tags=["operations"])


class CheckStatus(StrEnum):
    """Outcome of a single readiness check."""

    ok = "ok"
    unavailable = "unavailable"


class ReadinessStatus(StrEnum):
    """Aggregate readiness of the service."""

    ready = "ready"
    degraded = "degraded"


class LivenessResponse(ResponseModel):
    """`/healthz` payload."""

    status: str


class ReadinessResponse(ResponseModel):
    """`/readyz` payload.

    Check names are stable; their values are `ok` or `unavailable`. No check
    reports why a dependency is unavailable, because that reason may name
    internal hosts.
    """

    status: ReadinessStatus
    checks: dict[str, CheckStatus]


def build_readiness_response(
    settings: Settings, database: Database | None = None
) -> ReadinessResponse:
    """Evaluate readiness dependencies.

    Optional connectors are excluded deliberately: a missing connector key
    disables that connector, it does not make the service unready.

    The database check is a real round trip when a pool exists, because a
    configured but unreachable database is exactly the case readiness has to
    catch. The probe swallows the driver error and reports only `unavailable`;
    the reason goes to the logs, where it cannot name an internal host to a
    caller.
    """
    if settings.database_url is None:
        database_status = CheckStatus.unavailable
    elif database is None:
        database_status = CheckStatus.unavailable
    else:
        database_status = CheckStatus.ok if database.check_connection() else CheckStatus.unavailable
    checks = {
        "configuration": CheckStatus.ok,
        "database": database_status,
    }
    status = (
        ReadinessStatus.ready
        if all(check is CheckStatus.ok for check in checks.values())
        else ReadinessStatus.degraded
    )
    return ReadinessResponse(status=status, checks=checks)


@router.get("/healthz", summary="Process liveness")
def read_liveness() -> LivenessResponse:
    """Report that the process is alive. Dependencies are not checked here."""
    return LivenessResponse(status="ok")


@router.get("/readyz", summary="Dependency readiness")
def read_readiness(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    """Report whether the service is ready to accept product traffic."""
    database: Database | None = getattr(request.app.state, "database", None)
    readiness = build_readiness_response(settings, database)
    if readiness.status is ReadinessStatus.degraded:
        response.status_code = 503
    return readiness
