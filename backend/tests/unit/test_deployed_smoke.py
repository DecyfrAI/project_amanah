"""The deployed smoke probe checks access boundaries without mutation."""

import httpx2
import pytest

from amanah.observability.smoke import run_smoke


def test_smoke_checks_health_anonymous_denial_and_authenticated_reads() -> None:
    seen: list[tuple[str, bool]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        authenticated = request.headers.get("Authorization") == "Bearer demo-token"
        seen.append((request.url.path, authenticated))
        if request.url.path in {"/healthz", "/readyz"}:
            return httpx2.Response(200, json={"status": "ok"})
        if request.url.path == "/openapi.json":
            return httpx2.Response(
                200,
                json={
                    "paths": {
                        "/healthz": {"get": {}},
                        "/v1/me": {"get": {}},
                        "/v1/items/{item_id}": {"get": {}},
                    }
                },
            )
        if not authenticated:
            return httpx2.Response(401, json={"error": {"code": "AUTHENTICATION_REQUIRED"}})
        return httpx2.Response(200, json={"ok": True})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        run_smoke("https://api.example.test", "demo-token", client=client)

    assert seen == [
        ("/healthz", False),
        ("/readyz", False),
        ("/openapi.json", False),
        ("/v1/me", False),
        ("/v1/items/00000000-0000-0000-0000-000000000000", False),
        ("/v1/me", True),
        ("/v1/dashboard", True),
    ]


def test_smoke_refuses_an_anonymously_open_product_route() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/openapi.json":
            return httpx2.Response(200, json={"paths": {"/v1/me": {"get": {}}}})
        return httpx2.Response(200, json={"ok": True})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="anonymous product route"):
            run_smoke("https://api.example.test", "demo-token", client=client)
