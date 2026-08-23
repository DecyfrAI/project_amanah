# Amanah backend

FastAPI service for Project Amanah: an authenticated research API over monitored
Islamophobia and anti-Muslim hate data.

Bounded context: it owns the `/v1` product contract, the authentication boundary,
and (from B-S3 onward) the relational store behind it. Only `/healthz` and
`/readyz` are reachable without a verified session.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) 0.11 or newer
- Python 3.13 (uv installs it from `.python-version` if it is missing)

## Quick start

```bash
uv sync --locked --project backend --all-groups
```

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env`, then run the service:

```bash
uv run --project backend --env-file backend/.env uvicorn amanah.main:create_app --factory --reload
```

The API listens on http://127.0.0.1:8000. Check it with:

```bash
curl http://127.0.0.1:8000/healthz
```

## Commands

Run these from the repository root. Every one was executed against this
checkout.

| Purpose | Command |
|---|---|
| Install | `uv sync --locked --project backend --all-groups` |
| Tests | `uv run --project backend pytest backend/tests` |
| One test file | `uv run --project backend pytest backend/tests/unit/test_settings.py` |
| One test by node ID | `uv run --project backend pytest backend/tests/unit/test_settings.py::test_data_mode_defaults_to_fixture` |
| Lint | `uv run --project backend ruff check backend/src backend/tests` |
| Format check | `uv run --project backend ruff format --check backend/src backend/tests` |
| Format write | `uv run --project backend ruff format backend/src backend/tests` |
| Type check | `uv run --project backend mypy backend/src backend/tests` |
| Import/startup check | `uv run --project backend python -c "from amanah.main import create_app; create_app()"` |

The import/startup check reads the environment, so give it configuration:
`uv run --project backend --env-file backend/.env python -c ...`.

Tests never read the ambient environment — every fixture builds its own
synthetic settings and signs its own throwaway tokens.

## Configuration

Configuration comes from the process environment and nowhere else. `backend/.env`
is a convenience for local runs, loaded by `uv --env-file`, not by the
application. Every variable is documented in
[`.env.example`](./.env.example).

| Variable | Required | Purpose |
|---|---|---|
| `APP_ORIGIN` | yes | Comma-separated browser origins allowed by CORS |
| `SUPABASE_URL` | yes | Supabase project URL; the token issuer is derived from it |
| `SUPABASE_JWT_SECRET` | yes | Verifies access tokens; at least 32 characters |
| `DATABASE_URL` | readiness | Postgres connection string; `/readyz` degrades without it |
| `APP_ENV`, `LOG_LEVEL`, `DATA_MODE` | no | Environment name, log level, fixture/live/fallback mode |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | no | Enables the Gemini connector when both are set |
| `YOUTUBE_API_KEY`, `NEWS_API_KEY` | no | Enable their connectors |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | no | Reserved; Reddit stays disabled pending approval |

Missing core configuration fails startup with a message that names the offending
variables and never their values. A missing optional connector credential
disables only that connector.

## API surface

The OpenAPI document is the contract and is served at `/openapi.json`. No
interactive documentation UI is mounted, because serving one would require
relaxing the response Content-Security-Policy to allow third-party scripts.

Save the contract locally with:

```bash
curl http://127.0.0.1:8000/openapi.json -o openapi.json
```

| Route | Auth | Purpose |
|---|---|---|
| `GET /healthz` | none | Process liveness; checks no dependencies |
| `GET /readyz` | none | Dependency readiness; `503` when degraded |
| `GET /v1/me` | bearer | The caller's verified identity and role |

Every failing request returns the same envelope:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication is required.",
    "request_id": "req_0f3c…",
    "retryable": false,
    "details": {}
  }
}
```

## Layout

```text
src/amanah/
├── api/            # routes, dependencies, error mapping, response security headers
│   ├── schemas/    # the /v1 request and response contract
│   └── v1/         # authenticated product router
├── auth/           # access-token verification and the role model
├── domain/         # controlled enums shared across API, storage, and ingestion
├── observability/  # request correlation and structured logging
├── settings.py     # validated configuration
└── main.py         # application factory
tests/{unit,integration,contract}/
```

## Links

- Product specification: [`../docs/spec.md`](../docs/spec.md)
- Implementation plan: [`../docs/backend-implementation-plan.md`](../docs/backend-implementation-plan.md)
- Decision records: [`../docs/adr/`](../docs/adr/)
- Engineering rules: [`../rules/`](../rules/)
