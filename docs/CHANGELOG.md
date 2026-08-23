# Changelog

All notable project changes are documented here using the Keep a Changelog structure.

## [Unreleased]

### Added

- `docs/frontend-backend-reconciliation.md`: the audited gap list (G1–G11) between the
  shipped frontend and the planned backend, the direction agreed for each, and the
  disposition of the 23 August 2026 product-owner change requests (news relevance
  filtering, database-checked dedupe, no profanity censoring, RSS allowlist, assistant
  default queries, image classification, per-run insights, five-year backfill).
- Backend plan/todo steps B-S24 (bounded historical backfill), B-S25 (grounded dashboard
  assistant), B-S26 (image-evidence catalog and classification per ADR 0007), and B-S27
  (insight snapshots, discussion, captures, and `PATCH /v1/me` per ADR 0004), plus
  B-S9.7–B-S9.9 (RSS allowlist, topical relevance filter, context news stream contract),
  B-S12.9 (stored text is never profanity-filtered), and B-S15.10 (insights refresh on
  every ETL run). B-S25–B-S27 require an additive `spec.md` §13 amendment before code.
- Frontend todo step F-S21 (live-backend contract reconciliation: bearer token,
  `/v1/dashboard` adoption, items/filters reshape, bundle split, report-flow and
  public-`/resources` decisions) and a status note that the checklist describes scope,
  not progress.
- Spec v2.2 (23 August 2026, product-owner decisions closing the reconciliation):
  additive §13.2 rows for the insights/discussion/captures/viewer-post routes
  (ADR 0004), `POST /v1/assistant/query`, and `GET /v1/image-examples` /
  `POST /v1/image-classifications` (ADR 0007); FR-TOS-010 hybrid assisted-report flow
  (policy catalog where an official reporting form exists, allow-listed email-style
  draft otherwise, never auto-sent; also B-S18.9); and the static lesson library at
  `/resources` recorded as a public marketing surface that must never fetch a `/v1`
  product API (ADR 0008, §7.1/§7.2, `AGENTS.md` aligned). Qur'anic-translation
  verification and Supabase credentials remain deferred; F-S9/F-S21.1 wait on the
  credentials.

- Relational schema for sources, approved source seeds, dataset packages and import runs,
  collection runs, canonical content, predictions, review tasks and events, metric buckets,
  news links, insight snapshots, user profiles, submissions, disputes, contribution events,
  platform policies, policy matches, prepared reports, curated resources, and research
  reports. UUID keys, UTC timestamps, native enum types built from the published `/v1`
  vocabulary, documented unique and check constraints, and only query-driven indexes.
- Append-only history: predictions, review events, and contribution events refuse updates
  and deletes at the database, and a research-report snapshot becomes immutable once it is
  `ready`.
- Authenticated-safe projections. Repositories read `authenticated_*` views and never a base
  table; those views have no column for encrypted text, normalized model input, private
  storage keys, provider payloads, or provider-side item identifiers.
- Row-level security enabled and forced on every product table, with owner, reviewer, and
  administrator boundaries. Every privilege is revoked from `anon` and `PUBLIC` on every
  table, view, sequence, and function, and no policy names `anon`. Each request publishes
  its verified caller into the database session, so owner-scoped reads are filtered by the
  database as well as by the application.
- Authenticated `GET /v1/dashboard`, `/v1/items`, `/v1/items/{id}`, `/v1/news`,
  `/v1/filters`, `/v1/resources`, `/v1/methodology`, and `/v1/connections`. Validated date,
  content, platform, dataset, geography, narrative, severity, review-state, and confidence
  filters; documented stable sorts; and keyset pagination whose cursor is rejected if it was
  issued for a different sort.
- Every rate returns its numerator, denominator, window, source scope, coverage, and data
  mode. A day with no computed bucket is returned as a gap with null counts rather than as
  zero, and stale or partial coverage is stated in the response.
- Datapack records publish source and platform `N/A` while dataset provider, name, version,
  licence, and landing page remain separate provenance and separate filters.
- A live database probe behind `/readyz`, explicit connect and statement timeouts, and a
  bounded connection pool, all configurable.
- Alembic migrations as a separate one-off process, with a test suite that creates an empty
  scratch database, applies every migration to it, and drops it afterwards.
- Backend service foundation: a uv-managed FastAPI application factory, pinned dependencies, and lint, format, type-check, and test commands verified from the repository root.
- Unauthenticated `GET /healthz` (process liveness) and `GET /readyz` (dependency readiness, `503` when the database is not configured).
- Authenticated `GET /v1/me`, returning the caller's server-verified identifier and role.
- The `/v1` contract vocabulary: controlled enums for source, platform, content, relevance, stance, hate type, severity, confidence, review, contribution, submission, and job states, plus authenticated-safe dashboard, item, and resource models, cursor pagination, and validated filters and sorts.
- One safe error envelope with a stable code, safe message, request ID, retryability flag, and safe details, returned by every failing operation.
- Server-side Supabase access-token verification with reusable authenticated-user, reviewer, administrator, and resource-ownership checks. Authentication is attached to the `/v1` router, so a new product endpoint cannot be anonymous by omission.
- Request correlation via `X-Request-Id` and structured JSON logs that carry it, with tokens, secrets, tracebacks, and raw source content excluded.
- Baseline response security headers and CORS restricted to the configured origins.
- `backend/README.md` and `backend/.env.example` documenting every variable the service reads, with no real values. An optional variable left at its `<REDACTED>` placeholder is treated as unset, so a connector bootstrapped from the template stays disabled rather than being called with a placeholder credential.

### Changed

- Item projections report an unanalysed item honestly: `relevance`, `stance`, `severity`,
  `confidence_tier`, and the model disclosure are null until a successful prediction exists,
  and `is_classified` says so. Defaulting them to `uncertain` would have attributed a label
  to the model that it never produced.
- `/readyz` now makes a real round trip to the database instead of reporting only that a
  connection string is configured, so a configured-but-unreachable database is caught by
  readiness rather than by the first product request.
- Limited anonymous product access to the marketing and authentication-entry surfaces. Dashboard, content, methodology, resources, reports, contributions, reviewer/admin views, and all `/v1` product endpoints now require authentication in the governing specification and implementation plans.

