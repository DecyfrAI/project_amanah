# Changelog

All notable project changes are documented here using the Keep a Changelog structure.

## [Unreleased]

### Added

- Backend service foundation: a uv-managed FastAPI application factory, pinned dependencies, and lint, format, type-check, and test commands verified from the repository root.
- Unauthenticated `GET /healthz` (process liveness) and `GET /readyz` (dependency readiness, `503` when the database is not configured).
- Authenticated `GET /v1/me`, returning the caller's server-verified identifier and role.
- The `/v1` contract vocabulary: controlled enums for source, platform, content, relevance, stance, hate type, severity, confidence, review, contribution, submission, and job states, plus authenticated-safe dashboard, item, and resource models, cursor pagination, and validated filters and sorts.
- One safe error envelope with a stable code, safe message, request ID, retryability flag, and safe details, returned by every failing operation.
- Server-side Supabase access-token verification with reusable authenticated-user, reviewer, administrator, and resource-ownership checks. Authentication is attached to the `/v1` router, so a new product endpoint cannot be anonymous by omission.
- Request correlation via `X-Request-Id` and structured JSON logs that carry it, with tokens, secrets, tracebacks, and raw source content excluded.
- Baseline response security headers and CORS restricted to the configured origins.
- `backend/README.md` and `backend/.env.example` documenting every variable the service reads, with no real values.

### Changed

- Limited anonymous product access to the marketing and authentication-entry surfaces. Dashboard, content, methodology, resources, reports, contributions, reviewer/admin views, and all `/v1` product endpoints now require authentication in the governing specification and implementation plans.

