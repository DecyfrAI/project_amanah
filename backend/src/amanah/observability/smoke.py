"""Deployed smoke checks with no mutation and no provider calls."""

from __future__ import annotations

import os
import re

import httpx2


def run_smoke(base_url: str, access_token: str, *, client: httpx2.Client | None = None) -> None:
    owned = client is None
    session = client or httpx2.Client(timeout=15.0)
    try:
        for path in ("/healthz", "/readyz"):
            response = session.get(f"{base_url.rstrip('/')}{path}")
            response.raise_for_status()
        contract = session.get(f"{base_url.rstrip('/')}/openapi.json")
        contract.raise_for_status()
        paths = contract.json().get("paths", {})
        checked = 0
        for template, operations in paths.items():
            if not str(template).startswith("/v1"):
                continue
            concrete = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", template)
            for method in operations:
                if method.casefold() not in {"get", "post", "patch", "put", "delete"}:
                    continue
                denied = session.request(method.upper(), f"{base_url.rstrip('/')}{concrete}")
                if denied.status_code != 401:
                    raise RuntimeError("anonymous product route did not deny access")
                checked += 1
        if checked == 0:
            raise RuntimeError("deployment published no product routes")
        headers = {"Authorization": f"Bearer {access_token}"}
        for path in ("/v1/me", "/v1/dashboard"):
            response = session.get(f"{base_url.rstrip('/')}{path}", headers=headers)
            response.raise_for_status()
    finally:
        if owned:
            session.close()


def main() -> int:
    base_url = os.environ.get("AMANAH_SMOKE_BASE_URL")
    access_token = os.environ.get("AMANAH_SMOKE_ACCESS_TOKEN")
    if not base_url or not access_token:
        print("AMANAH_SMOKE_BASE_URL and AMANAH_SMOKE_ACCESS_TOKEN are required.")
        return 2
    run_smoke(base_url, access_token)
    print("Deployed smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
