"""Per-IP API protection with correct Retry-After response metadata.

User mutations retain their durable database-backed per-user limits. This outer
limit bounds anonymous authentication pressure and read floods before they can
consume a database connection. It is an instance safety limit; the deployment
edge must apply the same ceiling across instances as documented in the runbook.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic, perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from amanah.api.errors import build_error_response
from amanah.api.schemas.errors import ErrorCode
from amanah.observability.metrics import MetricName, record_metric


@dataclass(slots=True)
class _Window:
    started_at: float
    count: int = 0


class FixedWindowIpLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._windows: dict[str, _Window] = {}
        self._lock = Lock()

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int, int]:
        moment = monotonic() if now is None else now
        with self._lock:
            window = self._windows.get(key)
            if window is None or moment - window.started_at >= self.window_seconds:
                window = _Window(started_at=moment)
                self._windows[key] = window
            window.count += 1
            retry_after = max(1, int(self.window_seconds - (moment - window.started_at) + 0.999))
            remaining = max(0, self.limit - window.count)
            return window.count <= self.limit, remaining, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, limit: int, window_seconds: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limiter = FixedWindowIpLimiter(limit=limit, window_seconds=window_seconds)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in {"/healthz", "/readyz"}:
            return await call_next(request)
        client_key = request.client.host if request.client is not None else "unknown"
        allowed, remaining, retry_after = self._limiter.check(client_key)
        response: Response
        if not allowed:
            route = "/v1/*" if request.url.path.startswith("/v1/") else "other"
            response = build_error_response(
                code=ErrorCode.rate_limited,
                status_code=429,
                message="Too many requests. Please retry later.",
                details={"retry_after_seconds": retry_after},
                retry_after_seconds=retry_after,
            )
        else:
            started_at = perf_counter()
            response = await call_next(request)
            route = str(getattr(request.scope.get("route"), "path", "other"))
            record_metric(
                MetricName.api_duration,
                round((perf_counter() - started_at) * 1000, 3),
                method=request.method,
                route=route,
                status_class=f"{response.status_code // 100}xx",
            )
        record_metric(
            MetricName.api_requests,
            method=request.method,
            route=route,
            status_class=f"{response.status_code // 100}xx",
        )
        response.headers["X-RateLimit-Limit"] = str(self._limiter.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(retry_after)
        return response
