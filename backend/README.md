# Amanah backend

FastAPI service for Project Amanah: an authenticated research API over monitored
Islamophobia and anti-Muslim hate data.

Bounded context: it owns the `/v1` product contract, the authentication boundary,
and the relational store behind it. Only `/healthz` and `/readyz` are reachable
without a verified session.

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

Fill in `backend/.env`, apply the migrations, then run the service:

```bash
uv run --project backend --env-file backend/.env alembic -c backend/alembic.ini upgrade head
```


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
| Migrate | `uv run --project backend --env-file backend/.env alembic -c backend/alembic.ini upgrade head` |
| Preview migration SQL | the same command with `upgrade head --sql` |
| One test file | `uv run --project backend pytest backend/tests/unit/test_settings.py` |
| One test by node ID | `uv run --project backend pytest backend/tests/unit/test_settings.py::test_data_mode_defaults_to_fixture` |
| Lint | `uv run --project backend ruff check backend/src backend/tests backend/migrations` |
| Format check | `uv run --project backend ruff format --check backend/src backend/tests backend/migrations` |
| Format write | `uv run --project backend ruff format backend/src backend/tests backend/migrations` |
| Type check | `uv run --project backend mypy backend/src backend/tests` |
| Import/startup check | `uv run --project backend python -c "from amanah.main import create_app; create_app()"` |
| Sync reviewed configuration | `uv run --project backend --env-file backend/.env amanah-etl sync-config` |
| ETL fixture run (no network) | `uv run --project backend --env-file backend/.env amanah-etl run --source fixtures --mode fixture` |
| ETL dry run | the same command with `--dry-run` |
| Historical backfill | `uv run --project backend --env-file backend/.env amanah-etl backfill --source fixtures --from 2021-08-23 --to 2026-08-23` |

The import/startup check reads the environment, so give it configuration:
`uv run --project backend --env-file backend/.env python -c ...`.

Tests never read the ambient environment — every fixture builds its own
synthetic settings and signs its own throwaway tokens.

The tests under `tests/db/` need a real Postgres. Point them at a server they may
create and drop scratch databases on:

```bash
AMANAH_TEST_DATABASE_URL=postgresql://user:password@host:5432/postgres uv run --project backend pytest backend/tests
```

Each run creates its own empty database, applies every migration to it, and drops
it afterwards, so the migrations are proven from empty on every run and no test
can see another's data. Without the variable those tests skip, and the skip is
reported rather than passing silently.

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
| `DATABASE_URL` | readiness | Postgres connection string; `/readyz` degrades and `/v1` product reads return `503` without it |
| `DATABASE_CONNECT_TIMEOUT_SECONDS`, `DATABASE_STATEMENT_TIMEOUT_MS`, `DATABASE_POOL_SIZE` | no | Explicit connection and query bounds, and pool size |
| `APP_ENV`, `LOG_LEVEL`, `DATA_MODE` | no | Environment name, log level, fixture/live/fallback mode |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | no | Enables the Gemini connector when both are set |
| `YOUTUBE_API_KEY`, `NEWS_API_KEY` | no | Enable their connectors |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | no | Reserved; Reddit stays disabled pending approval |
| `CONTENT_ENCRYPTION_KEY` | no | Base64 of 32 bytes. Encrypts permitted original text at rest; absent means the original is not retained at all, never stored as plaintext |
| `SOURCE_CONFIG_DIRECTORY` | no | Reviewed source and seed YAML; defaults to `config/` in the repository |
| `HTTP_CONNECT_TIMEOUT_SECONDS`, `HTTP_READ_TIMEOUT_SECONDS`, `HTTP_TOTAL_TIMEOUT_SECONDS` | no | Explicit bounds on every outbound provider call |
| `HTTP_MAX_RESPONSE_BYTES`, `HTTP_MAX_REDIRECTS` | no | Byte budget and redirect limit for provider and user-URL retrieval |

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
| `GET /v1/dashboard` | bearer | Coverage, deterministic metrics, trend, headlines |
| `GET /v1/items` | bearer | Filtered, sorted, cursor-paginated items |
| `GET /v1/items/{id}` | bearer | One item with its model disclosure and limitations |
| `GET /v1/news` | bearer | Context news stream: publisher metadata only, never a classification |
| `GET /v1/admin/runs` | bearer, admin | Collection runs, newest dispatch first |
| `POST /v1/admin/runs` | bearer, admin | Dispatch one bounded run; `200` on a redelivered key |
| `GET /v1/admin/runs/{id}` | bearer, admin | One run and the stages beneath it |
| `GET /v1/filters` | bearer | Filter values present in the data, plus query bounds |
| `GET /v1/resources` | bearer | Reviewed, published education resources |
| `GET /v1/methodology` | bearer | Sampling, taxonomy, model, coverage, and limitations |
| `GET /v1/connections` | bearer | Safe connector state; never a key or a provider error |

`/v1/news` is deliberately not an item projection. An ingested article coincides
with the monitoring window; it is not an Amanah finding, so the response carries
no hate label, score, severity, or review state, and the projection behind it has
no column for one. Classified news *item cards* are served from `/v1/items`.

Every rate carries its numerator, denominator, window, source scope, coverage,
and data mode. A window with no computed bucket is returned as a gap with null
counts — never as zero.

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
├── db/             # models, migrations' target metadata, sessions, repositories
│   ├── models/     # one module per area of the schema
│   ├── views.py    # read handles for the authenticated-safe projections
│   └── session.py  # engine, and the per-request transaction that scopes reads
├── domain/         # controlled enums shared across API, storage, and ingestion
├── jobs/           # run and job state machines, leases, retry schedule
├── ingestion/      # adapter contract, reviewed configuration, sources, pipeline, CLI
│   ├── fixtures/   # the deterministic corpus that needs no network
│   ├── news/       # reviewed RSS and Atom allowlist
│   ├── youtube/    # official Data API only
│   ├── datapacks/  # manifest-validated importer, never a crawler
│   └── urls/       # SSRF-safe retrieval of user-submitted URLs
├── canonical/      # normalization, context, hashing, dedupe, encrypted storage
├── metrics/        # deterministic aggregates, coverage, and their disclosures
├── resources/      # curated resources and the published methodology
├── observability/  # request correlation and structured logging
├── settings.py     # validated configuration
└── main.py         # application factory
migrations/         # Alembic revisions; a separate one-off process
config/             # reviewed source and seed catalogue (repository root)
tests/{unit,integration,contract,db}/
```

## Data access

Repositories read `authenticated_*` views and never a base table. Those views
have no column for encrypted text, normalized model input, private storage keys,
provider payloads, or provider-side item identifiers, so an endpoint cannot
return one. Row-level security is enabled and forced on every product table, no
policy names `anon`, and each request publishes its verified caller into the
session so owner-scoped projections are filtered by the database as well as by
the application. See
[ADR 0004](../docs/adr/0004-read-product-data-only-through-authenticated-safe-views.md).

## Links

- Product specification: [`../docs/spec.md`](../docs/spec.md)
- Implementation plan: [`../docs/backend-implementation-plan.md`](../docs/backend-implementation-plan.md)
- Decision records: [`../docs/adr/`](../docs/adr/)
- Engineering rules: [`../rules/`](../rules/)
