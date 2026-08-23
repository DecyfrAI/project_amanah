# ⚙️ Backend Workflow

Self-contained playbook for server-side work: API contracts, services, business logic, the database, and migrations. This track folds in **API design** and **database design** because they are inseparable from backend implementation.

**Rules in scope:** `rules/backend.md`, `rules/api.md`, `rules/database.md` (all primary), `rules/security.md`, `rules/testing.md`, `rules/general.md`
**Upstream sources:** `sources/Microsoft_api-guidelines`, `sources/Stripe_api`, `sources/Zalando`, `sources/postgres`, `sources/Twelve Factor App.md`, `sources/Google_SRE_Workbook.md`

> Prerequisite: complete the shared phases in [../Workflow.md](../Workflow.md) — you need `spec.md`, `plan.md`, `AGENTS.md`, and `todo.md` with `[backend]` steps. Backend is usually the **first track to build** because the frontend depends on its contract.

---

## Build order

```
B0 Setup ─► B1 API contract ─► B2 DB schema ─► B3 Build loop (services/endpoints/migrations)
                                                     │
                                                     ▼
                                          B4 Security gate ─► B5 Tests ─► DoD
```

Design the **contract and schema first** (`api.md` §1.1 is contract-first; you cannot safely reverse-engineer either later).

---

## Step B0 — Setup (once per service)

**Checklist**
- [ ] Service scaffolded; 12-factor config (all config from env vars, fail-fast on missing)
- [ ] Structured JSON logging to stdout wired (timestamp, level, service, trace_id, span_id)
- [ ] `/healthz` (liveness) and `/readyz` (readiness) endpoints stubbed
- [ ] Migration tool chosen and wired into CI
- [ ] Integration-test harness with **testcontainers** (real Postgres), not mocks
- [ ] `.env.example` lists every variable with purpose + required/optional
- [ ] Linter + type-checker + zero-warning CI gate

### Prompt B0 — Scaffold the service

```
You are setting up a backend service. Follow rules/backend.md and Twelve-Factor.

Produce:
1. Service skeleton with config loaded ONLY from environment variables; startup FAILS LOUDLY
   on any missing required var (no silent defaults for required config).
2. Structured JSON logger to stdout: timestamp (ISO 8601 UTC), level, service, trace_id,
   span_id, message. Never log secrets or PII.
3. GET /healthz (liveness, NO dependency checks, <500ms) and GET /readyz (readiness, checks
   DB + critical deps).
4. Graceful SIGTERM handler: stop accepting connections → drain in-flight → release locks →
   flush telemetry → exit 0.
5. A .env.example documenting every variable (purpose, required/optional, placeholder).
6. An integration-test harness using testcontainers for a real Postgres.

Tech stack from spec: [PASTE relevant spec section]
```

---

## Step B1 — API Contract Design (before any endpoint code)

### Prompt B1 — OpenAPI contract

```
You are an API designer. Produce a complete OpenAPI 3.1 spec BEFORE any server code. The
spec is the contract — implementation follows it. Follow rules/api.md.

Rules:
- Resources are nouns; URLs never contain verbs. Non-CRUD ops use POST /thing/{id}:action.
- Collections are plural kebab-case (/payment-methods); JSON fields are camelCase;
  enums are SCREAMING_SNAKE_CASE and documented as extensible.
- Date/time = RFC 3339 (2024-06-01T14:30:00Z). Duration fields name the unit (ttlSeconds).
- Top-level responses are JSON objects — never bare arrays.
- Cursor-based pagination with { items, next, prev, self }; opaque cursors.
- POST/PATCH accept an Idempotency-Key header.
- All errors use RFC 9457 Problem Details (application/problem+json) with a machine-readable
  `code` and a `trace_id`/X-Request-Id.
- Version prefix on every path: /v1/...
- Per endpoint document: summary, request schema, and responses for 200/201, 400, 401, 403,
  404, 409, 429, 500. Same schema shape across GET/PUT/PATCH/POST; PATCH fields all optional.

Output: a complete docs/api/<service>.openapi.yaml.
Spec: [PASTE spec.md]
```

→ If this contract reflects an architecturally significant choice (new public API, breaking change), write an ADR (Prompt 2.3 in the hub).

---

## Step B2 — Database Schema Design (before any migration)

### Prompt B2 — PostgreSQL schema

```
You are a database architect. Design the PostgreSQL schema. Follow rules/database.md.

Rules:
- Identifiers lowercase_snake_case; tables are plural nouns.
- PK: bigint GENERATED ALWAYS AS IDENTITY (single DB) or UUIDv7 (distributed/exposed IDs).
- Every FK has a REFERENCES constraint AND its own index; ON DELETE is explicit (prefer RESTRICT).
- timestamptz NOT NULL DEFAULT now() for time; numeric for money; text for strings;
  boolean for flags. Never plain timestamp / float / varchar(n) / char(1).
- Every table: created_at. Mutable tables: updated_at via trigger.
- NOT NULL unless NULL has deliberate meaning. CHECK constraints enforce domain rules.
  UNIQUE enforces uniqueness at the DB, not the app.
- Soft delete (if needed): deleted_at + partial index WHERE deleted_at IS NULL.
- Aim for 3NF; denormalize only after a profiled problem, and document it.

Output:
1. ER description (entities, relationships, cardinalities).
2. Schema as an idempotent migration (up + down).
3. Each index with a one-line justification.
Spec: [PASTE spec.md]    API contract: [PASTE openapi.yaml]
```

---

## Step B3 — Build Loop (per `[backend]` step in todo.md)

```
1. Open todo.md → next [backend] step
2. Is it a schema change? → Prompt B-MIG.  Otherwise → Prompt B3.
3. Review: ownership boundaries, error handling, timeouts, idempotency
4. Run integration tests against real Postgres (testcontainers)
5. Run Prompt B-TEST for coverage
6. Touches auth / authz / payments / PII? → Prompt B-SEC (mandatory)
7. Check off todo.md → commit (e.g. "Implement B-step 6 from todo.md: POST /v1/orders")
```

### Prompt B3 — Implement a backend step

```
You are implementing a backend task. Follow the rules below strictly.

Rules (rules/backend.md):
- Service owns its data — no shared tables/queues across services; cross-service reads go
  through the owning service's API.
- All config from env vars; fail fast on missing config.
- Structured JSON logs to stdout; no secrets/PII/stack traces in logs.
- Every outbound call has an explicit, env-configurable timeout (connect + read).
- Retries: exponential backoff with jitter, max attempts, respect Retry-After; never retry
  non-idempotent ops without an idempotency guarantee.
- Circuit breaker on critical external deps; non-critical features degrade gracefully.
- Mutation endpoints support idempotency keys; consumers handle at-least-once delivery.

Rules (rules/api.md):
- Conform to the committed OpenAPI contract exactly. Reject unknown fields with 400.
- RFC 9457 error bodies with machine-readable `code`; correct status codes (4xx client, 5xx server).
- POST-create returns 201 + Location; DELETE returns 204 (even if already absent).

Rules (rules/security.md):
- Parameterized queries ONLY — never concatenate input into SQL.
- Server-side validation, allowlist approach, at every trust boundary; enforce max lengths.
- Authorization on EVERY request; verify resource ownership per request, not just at login.
- No internal details (stack traces, SQL, paths, versions) in external responses.

Rules (rules/testing.md):
- Integration tests use a real DB (testcontainers), not mocked repositories.
- Test unhappy paths: DB unavailable, malformed message, downstream timeout.

Current project state: [BRIEF: existing endpoints/services]
Contract: [PASTE relevant openapi.yaml paths]
Task: [PASTE the [backend] step from todo.md]

Extend and integrate; do not rewrite working code.
Reference files: rules/backend.md, rules/api.md, rules/security.md, rules/testing.md
```

### Prompt B-MIG — Database migration

```
You are writing a database migration. Follow rules/database.md.

Rules:
- One logical change per migration. Idempotent: IF NOT EXISTS / IF EXISTS; DO $$ blocks for constraints.
- Adding NOT NULL to an existing column: two steps — backfill nulls, THEN add the constraint.
- Adding a column to a large live table: ADD COLUMN with DEFAULT, drop the default later.
- Index on a large table: CREATE INDEX CONCURRENTLY (no write lock).
- Never DROP COLUMN in the same migration that removes app references — deploy app change first
  (expand/contract). Every new FK gets an index immediately. Wrap multi-row DML in a transaction.

Output:
1. Up migration (idempotent SQL).
2. Down migration (or an explicit note + reason if irreversible).
3. New indexes with one-line justification.
- Confirm backward-compatibility with the currently-deployed service version.

Current schema: [PASTE relevant tables]
Change needed: [DESCRIBE]
Reference files: rules/database.md, rules/backend.md (Deployment Readiness)
```

---

## Step B4 — Security Gate

### Prompt B-SEC — Backend security review

*Mandatory before merging any chunk touching auth, authorization, sessions, payments, or PII.*

```
You are a security reviewer doing a threat model + code review. Be adversarial — find
problems, don't approve. Per finding: Severity | Location (file:line) | Issue | Fix.

Checklist (rules/security.md):

Authentication:
[ ] Rate limiting on login/reset/MFA/registration; throttle by account, not just IP
[ ] Generic, constant-time failure messages (no user enumeration via wording or timing)
[ ] New session ID issued after login; session destroyed server-side on logout
[ ] Passwords hashed with Argon2id/scrypt/bcrypt; constant-time verify; never reversible
[ ] Re-auth required before sensitive operations

Authorization:
[ ] Authz enforced on EVERY request (incl. AJAX/API), server-side
[ ] Ownership verified against the specific resource per request
[ ] No guessable sequential IDs exposed without an ownership check
[ ] Default-deny; 403 + logged on failure; no sensitive context leaked

Input / Output / Data:
[ ] Server-side allowlist validation; parameterized queries; max lengths enforced
[ ] Context-aware output encoding; no stack traces/SQL/paths in responses
[ ] File uploads (if any): magic-byte type check, size cap, stored outside web root, renamed

Secrets / Deps / Transport:
[ ] No hardcoded secrets; none in logs; injected at runtime
[ ] New deps pinned; no critical/high CVEs
[ ] TLS enforced; security headers set (HSTS, nosniff, frame-deny, CSP)

Changes to review: [PASTE DIFF]
Reference files: rules/security.md
```

---

## Step B5 — Tests

### Prompt B-TEST — Backend tests

```
You are writing backend tests. Follow rules/testing.md (pyramid: ~70% unit / 20% integration / 10% E2E).

- Unit: hermetic, <100ms, one reason to fail, behavior not implementation; cover boundaries,
  empty, and null inputs.
- Integration: real dependencies via testcontainers; each test isolated (own schema or rolled-back
  transaction); test error paths (DB down, malformed input, downstream 500/timeout).
- Mock ONLY at process boundaries (external HTTP, email, payment gateway) — never the DB, never
  the system under test. Unhappy-path mocks (500/timeout) must be tested explicitly.
- Idempotency: a retried mutation with the same key produces one side effect.
- Every bug fix: a regression test that fails on the unfixed code, tagged with the ticket ID.

Code to test: [PASTE implementation]
Reference files: rules/testing.md, rules/backend.md
```

---

## Definition of Done (Backend)

- [ ] Implementation matches the committed OpenAPI contract; unknown fields rejected
- [ ] Config from env (fail-fast); structured logs with trace_id; explicit timeouts on outbound calls
- [ ] Errors are RFC 9457 with machine-readable codes; no internal leakage
- [ ] Migrations idempotent + backward-compatible; every FK indexed
- [ ] Authz checked per request; B-SEC passes for sensitive paths
- [ ] Integration tests on real Postgres; unhappy paths covered; regression test for any fix
- [ ] `/healthz` + `/readyz` accurate; graceful shutdown verified
- [ ] Lint + type-check + tests green locally

→ Hand off to [frontend.md](frontend.md) (now that the contract is live) and [devops.md](devops.md) for release.
