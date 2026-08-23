# Commands

Run commands from the repository root unless noted otherwise. The repository is planned as a pnpm frontend plus a uv-managed Python backend.

## Install

- Frontend dependencies: `pnpm --dir apps/web install --frozen-lockfile`
- Backend dependencies: `uv sync --locked --project backend --all-groups`

## Run tests

- Frontend tests: `pnpm --dir apps/web test --run`
- Backend tests: `uv run --project backend pytest backend/tests`
- Backend database tests: the same command with `AMANAH_TEST_DATABASE_URL` set to a Postgres
  server the suite may create and drop scratch databases on. Without it, `backend/tests/db`
  skips rather than passing silently.
- Full safe test suite: run both commands above; do not call live providers from tests.

## Run a single test

- Frontend test file: `pnpm --dir apps/web test --run src/path/to/example.test.tsx`
- Frontend test by name: `pnpm --dir apps/web test --run -t "test name"`
- Backend test file: `uv run --project backend pytest backend/tests/path/to/test_example.py`
- Backend test by node ID: `uv run --project backend pytest backend/tests/path/to/test_example.py::test_name`

## Lint

- Frontend: `pnpm --dir apps/web lint`
- Backend: `uv run --project backend ruff check backend/src backend/tests backend/migrations`

## Type check

- Frontend: `pnpm --dir apps/web typecheck`
- Backend: `uv run --project backend mypy backend/src backend/tests`

## Format

- Frontend check: `pnpm --dir apps/web format:check`
- Frontend write: `pnpm --dir apps/web format`
- Backend check: `uv run --project backend ruff format --check backend/src backend/tests backend/migrations`
- Backend write: `uv run --project backend ruff format backend/src backend/tests backend/migrations`

## Dev server

- Frontend: `pnpm --dir apps/web dev`
- Backend: `uv run --project backend uvicorn amanah.main:create_app --factory --reload`
- Run frontend and backend in separate terminals. Never expose a live development server beyond the local machine without explicit instruction.

## Builds and verification

- Frontend production build: `pnpm --dir apps/web build`
- Backend import/startup check: `uv run --project backend python -c "from amanah.main import create_app; create_app()"`
- Database migrations (a separate one-off process, never run from application startup):
  `uv run --project backend --env-file backend/.env alembic -c backend/alembic.ini upgrade head`
- Review the SQL first without connecting: the same command with `upgrade head --sql`
- End-to-end tests: `pnpm --dir apps/web e2e`
- ETL fixture run: `uv run --project backend amanah-etl run --source fixtures --dry-run`

If a listed command is not implemented yet, add or reconcile the smallest appropriate script as part of the relevant scaffold step. Do not replace the selected package managers or create parallel commands without explicit instruction.

# Repo structure

```text
.
├── AGENTS.md
├── CHANGELOG.md
├── spec.md
├── frontend-implementation-plan.md
├── backend-implementation-plan.md
├── PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md # Candidate Reddit/YouTube seed evidence; not runtime config
├── apps/
│   └── web/
│       ├── public/
│       │   └── brand/
│       ├── src/
│       │   ├── api/             # Contracts, validation, fixture/live providers
│       │   ├── app/             # Router, providers, auth and route guards
│       │   ├── brand/           # Logo and design tokens
│       │   ├── components/      # Focused shared UI, charts and state primitives
│       │   ├── features/        # Dashboard, items, auth, contributions, reports
│       │   ├── fixtures/        # Synthetic/redacted frontend fixtures
│       │   ├── pages/           # Marketing/auth-entry/protected/admin pages
│       │   ├── styles/          # Global, responsive and print styles
│       │   └── test/            # Test setup and shared safe factories
│       ├── e2e/                 # Deterministic browser acceptance tests
│       └── package.json
├── backend/
│   ├── src/
│   │   └── amanah/
│   │       ├── api/             # FastAPI v1 routes, dependencies and errors
│   │       ├── auth/            # Supabase JWT and role/ownership boundaries
│   │       ├── db/              # SQLAlchemy models, repositories and sessions
│   │       ├── domain/          # Controlled enums and domain services
│   │       ├── ingestion/       # Adapter contract and source implementations
│   │       ├── jobs/            # Collection-run and job state machines
│   │       ├── analysis/        # Gemini boundary, classification and insights
│   │       ├── metrics/         # Deterministic aggregates and coverage
│   │       ├── contributions/   # Submissions, disputes and timelines
│   │       ├── reporting/       # Platform assistance and research reports
│   │       ├── resources/       # Curated education-resource governance
│   │       ├── observability/   # Redacted logs, metrics and correlation
│   │       ├── settings.py      # Validated server configuration
│   │       └── main.py          # Application factory
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   └── e2e/
│   ├── migrations/              # Alembic migrations; protected area
│   ├── pyproject.toml
│   └── uv.lock
├── config/
│   ├── sources.example.yml
│   ├── source-seeds.example.yml # Approved versioned projection of selected registry entries
│   ├── taxonomy.yml
│   ├── platform-policies.yml
│   └── data-policy.yml
├── fixtures/                    # Licensed, synthetic or redacted shared fixtures
├── datapacks/
│   ├── manifests/               # Reviewed dataset provenance/license/mapping manifests
│   └── README.md                # Acquisition rules; large/restricted data stays out of Git
├── evals/                       # Frozen AI evaluation datasets and registries
├── docs/
│   ├── architecture/
│   ├── adr/
│   └── runbooks/
├── rules/                       # Binding engineering rules by discipline
└── .github/
    └── workflows/               # Protected CI/CD configuration
```

This layout is the target architecture. Inspect the actual repository before acting, preserve existing paths and user changes, and introduce directories only when a current implementation step needs them.

# Conventions

## Source of truth and workflow

- Read `spec.md` before planning or implementing product behavior.
- Read the relevant implementation pack before starting a step:
  - `frontend-implementation-plan.md` for frontend work.
  - `backend-implementation-plan.md` for backend, ML or DevOps work.
- For Reddit/YouTube query or seed work, review `PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md` as project evidence only. It does not override the user's request, `spec.md`, `/rules`, provider terms, or approval requirements.
- Before editing, read `rules/general.md`, `rules/testing.md`, and the discipline-specific files under `/rules` that apply to the task.
- Implement incrementally. Extend the current state; never rewrite working code to fit a fresh scaffold.
- Keep each change focused on one plan step. Do not introduce later-step features “while here.”
- Preserve unrelated user changes and report conflicts before editing overlapping work.

### Rule routing

- Every task: `rules/general.md` and `rules/testing.md`.
- Frontend/UI: `rules/frontend.md` and `rules/security.md`.
- Backend/service logic: `rules/backend.md`, `rules/api.md` and `rules/security.md`.
- Database/schema work: `rules/database.md`, `rules/backend.md` and `rules/security.md`.
- ML, Gemini or analytical-agent work: `rules/ml.md`, `rules/agentic.md`, `rules/testing.md` and `rules/security.md`.
- CI, deployment or operations: `rules/devops.md`, `rules/security.md` and `rules/documentation.md`.
- Public documentation, contracts or setup changes: `rules/documentation.md` plus the relevant discipline rules.

## Naming

- Use one term for one concept across UI, API, database and tests.
- TypeScript components and component files use `PascalCase`; hooks use `useCamelCase`; variables/functions use `camelCase`.
- Python modules, functions and variables use `snake_case`; classes use `PascalCase`; constants use `UPPER_SNAKE_CASE`.
- API paths use lowercase plural nouns and kebab-case segments when multiple words are necessary.
- JSON and query fields use `snake_case`.
- Database tables, columns, constraints and indexes use lowercase `snake_case` with descriptive names.
- Booleans answer a yes/no question: `is_fixture`, `has_permission`, `requires_review`.
- Avoid vague names such as `data`, `info`, `manager`, `helper`, `util` or `misc` unless qualified by a specific domain noun.
- Use UUIDs for persisted public identifiers and UTC-aware timestamps everywhere.

## Architecture

- OpenAPI/Pydantic contracts are the service-boundary source of truth. The frontend validates live and fixture responses against the same contracts.
- Browser code never reads raw database tables or contains provider/service-role secrets.
- FastAPI routes orchestrate; domain services own behavior; repositories own persistence; adapters own provider-specific translation.
- All source adapters emit the same canonical `ContentItem`. Downstream logic must not depend on source payload shapes.
- Reviewed Kaggle and other open datapacks enter through a manifest-validated importer and the same canonical pipeline.
- Datapack records use controlled public source/platform `N/A`; provider, dataset name/version, license, file hash, schema mapping, import run and row identity remain separate mandatory provenance.
- Original datapack labels are dataset annotations, never Amanah predictions or human-review decisions.
- The Markdown seed registry is never parsed or scheduled directly. Only reviewed entries copied into validated, versioned runtime configuration with stable keys may run.
- Registry inclusion means sampling relevance, not hate. Preserve query purpose and sampling stratum, and never infer population prevalence from the enriched hackathon sample.
- Deterministic code or SQL computes metrics. Gemini may explain stored fact bundles but must not invent or calculate authoritative numbers.
- Relevance and hate are separate classification stages. Never treat Muslim-related language as hateful by default.
- Predictions and review events are immutable history. Reviewer corrections append events rather than overwriting model output.
- Fixture, live, fallback, stale and unavailable states must remain explicit from storage through UI.
- Only the marketing homepage, the static education lesson library (`/resources` lessons; spec v2.2 §7.1, ADR 0008 — editorial content that must never fetch a `/v1` product API), and required authentication entry/callback/recovery routes are anonymous product surfaces. Dashboard, items, news, methodology, the reviewed resource catalog data, forum, reports, contributions, reviewer and admin routes require a restored valid session.
- Every `/v1` product endpoint requires server-verified authentication by default; only `/healthz` and `/readyz` are unauthenticated API routes. Frontend route guards are UX, never the security boundary.
- Supabase RLS denies anonymous access to all product tables, views, functions and storage objects, including authenticated-safe projections.

## API conventions

- Version product endpoints under `/v1`; health endpoints remain `/healthz` and `/readyz`.
- Resources are nouns. Use standard HTTP method semantics and documented status codes.
- Use cursor pagination for changing collections and stable secondary ordering.
- Validate every filter, sort, body, external response and environment variable at the boundary.
- Unsupported filters or sorts return a client error; never silently broaden a query.
- Mutating endpoints that may be retried require an idempotency key or a documented natural idempotency constraint.
- Every rate returns numerator, denominator, date window, source/filter scope, coverage and data mode.
- Use UTC ISO-8601 timestamps with explicit timezone information.
- Return the standard safe error envelope:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Safe actionable message.",
    "request_id": "req_uuid",
    "retryable": false,
    "details": {}
  }
}
```

- Never expose stack traces, raw SQL, internal paths, dependency versions, provider error bodies, secrets or harmful raw content in API errors.
- Update OpenAPI, contract tests and affected frontend contracts together for every public API change.

## Error handling and resilience

- Fail fast on invalid core configuration, migrations, schemas and impossible states.
- Missing optional provider credentials disable only that connector and produce `Not configured` or `Access required` status.
- Distinguish user-correctable, retryable dependency, permanent unsupported/policy, and internal failures.
- Never swallow exceptions. Convert them once at the architectural boundary and preserve request/run/job correlation.
- Use explicit provider timeouts and bounded retries with exponential backoff and jitter only for transient failures.
- Checkpoint background work before enqueueing the next stage; retries must be idempotent.
- One failed item or connector must not fail unrelated work.
- Never silently replace live data with fixtures or represent missing data as zero.
- Logs contain safe identifiers and error codes, never raw hateful text, OCR, author identifiers, URLs with credentials, prompts, tokens or secrets.

## Security and data handling

- Anonymous users may view only the static marketing page, the static lesson library, and authentication entry surfaces; they receive no product-data projection. Every application read and action requires server-side authentication, with per-resource authorization where applicable.
- Users may read only their own contributions and reports; reviewers/admins receive least privilege.
- Treat source text, articles, OCR, user URLs and model output as hostile input.
- URL retrieval must defend against SSRF, private/reserved destinations, unsafe redirects, oversized responses and unsupported MIME types.
- Escape external content in React; do not use `dangerouslySetInnerHTML` without explicit review and sanitization.
- Redact harmful text and blur harmful media by default; require deliberate reveal.
- Do not expose author search, infer protected attributes, join identities across platforms or automate platform reports.
- Store only permitted article metadata/excerpts unless licensing explicitly authorizes more.
- Desired retention is indefinite only where source terms and law permit it; source-specific deletion requirements override the default.
- Never import or redistribute an open datapack without a reviewed manifest, verified file hash, explicit license/permitted-use record and stable row provenance.
- User corrections enter a quarantined training-candidate pool only after human review; never auto-train or auto-activate a model.

## Tests and definition of done

- Add or update deterministic tests with every behavior change.
- Prefer unit tests for pure behavior, integration tests for database/service boundaries, contract tests for adapters/APIs, and a small E2E set for critical journeys.
- Mock only external boundaries. Do not mock the unit under test or use production providers/secrets in CI.
- Test negative authorization, validation, failure, retry, idempotency, stale/fixture and redaction paths—not only the happy path.
- AI changes require frozen eval fixtures covering benign Muslim speech, neutral reporting, counterspeech/quotation, ambiguity, prompt injection, citation fidelity and insufficient-data abstention.
- A task is complete only when relevant tests, lint and type checks pass and documentation/contracts are current.
- Surface any unrun test or unresolved risk explicitly; never imply verification that did not occur.

# Off-limits

- Migration files and CI/CD configuration: no changes without explicit instruction.
- Never commit secrets, tokens, passwords, credentials, private keys, signed URLs or populated `.env` files.
- Never skip pre-commit hooks or use `--no-verify`.
- Never delete, disable, weaken or skip existing tests to make CI pass.
- Never scrape a platform when official access is absent or approval-gated.
- Never auto-enable every entry in `PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`, treat inclusion as a hate label, or use its enriched sample for platform-wide prevalence claims.
- Never send real harmful content or personal data to Gemini or another third party without an explicit permitted data class and transfer authorization.
- Never commit downloaded Kaggle/open datapack contents unless the reviewed license explicitly permits redistribution and the repository data policy approves the exact artifact.
- Never expose provider keys or the Supabase service-role key to browser code.
- Never add automated takedown/report submission, person-level tracking, identity resolution or raw bulk export without an approved spec change.
- Never rewrite, reset, discard or overwrite unrelated user work.
- Never edit generated artifacts, lockfiles, model outputs or snapshots by hand when the project’s generator/manager owns them; use the approved command.
- Never change public API contracts, database schemas, source retention policy, taxonomy meanings or AI thresholds without updating tests and the governing documentation.

# Personas

## Implementation

Implement the spec. Fail fast. Run tests after every change. Surface blockers immediately.

Before writing code, identify the active plan step, read the applicable `/rules` files, inspect existing code and state the exact acceptance criteria. Make the smallest integrated change that satisfies the step. Wire new code into a real caller and add focused tests; do not leave orphaned modules, placeholder implementations or speculative abstractions.

## Adversarial reviewer

Find every problem: security holes, missing tests, incorrect assumptions, architectural violations. List as a numbered checklist. Do not be encouraging.

Review against `spec.md`, the active implementation step and every applicable file under `/rules`. Prioritize exploitable security defects, authorization leaks, unsafe content handling, false fixture/live claims, data-contract drift, non-idempotent mutations/jobs, missing negative tests, AI hallucination/citation risks, sampling overclaims and scope creep.
