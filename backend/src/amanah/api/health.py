"""Unauthenticated operational endpoints.

`/healthz` and `/readyz` are the only routes this service exposes without a
verified session. Neither returns secrets, connection strings, dependency
versions, or build identifiers.
"""

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from amanah.api.dependencies import get_settings
from amanah.api.schemas.base import ResponseModel
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


def build_readiness_response(settings: Settings) -> ReadinessResponse:
    """Evaluate readiness dependencies.

    Optional connectors are excluded deliberately: a missing connector key
    disables that connector, it does not make the service unready.

    The database check confirms that a connection target is configured. A live
    connectivity probe is added with the database layer in step B-S3; until then
    this reports configuration readiness only.
    """
    checks = {
        "configuration": CheckStatus.ok,
        "database": (
            CheckStatus.ok if settings.database_url is not None else CheckStatus.unavailable
        ),
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
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    """Report whether the service is ready to accept product traffic."""
    readiness = build_readiness_response(settings)
    if readiness.status is ReadinessStatus.degraded:
        response.status_code = 503
    return readiness
