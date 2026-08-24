"""The `/v1` product router.

Authentication is attached to the router, not to individual operations, so every
endpoint mounted here requires a verified session by default. The bearer scheme
is declared as a router dependency as well, which is what makes each operation
carry a security requirement in the published OpenAPI document.
"""

from fastapi import APIRouter, Depends

from amanah.api.dependencies import bearer_scheme, require_authenticated_user
from amanah.api.schemas.errors import ErrorEnvelope
from amanah.api.v1 import admin, assistant, catalogue, dashboard, images, items, me, news

v1_router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(bearer_scheme), Depends(require_authenticated_user)],
    responses={
        401: {"model": ErrorEnvelope, "description": "Authentication is required."},
        403: {"model": ErrorEnvelope, "description": "The caller lacks access."},
    },
)

v1_router.include_router(me.router)
v1_router.include_router(dashboard.router)
v1_router.include_router(items.router)
v1_router.include_router(news.router)
v1_router.include_router(catalogue.router)
v1_router.include_router(assistant.router)
v1_router.include_router(images.router)
v1_router.include_router(admin.router)
