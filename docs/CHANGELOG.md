# Changelog

All notable project changes are documented here using the Keep a Changelog structure.

## [Unreleased]

### Added

- **Milestone 6 — governed resources and immutable research reports (B-S19–B-S20).**
  Reviewer/admin resource creation, revision, explicit human-confirmed publication, archive,
  and append-only audit history; published wording changes return to draft and only reviewed
  entries reach authenticated base-role readers. Authenticated filter-scoped research-report
  generation now freezes data and methodology versions, coverage, denominators, selected
  aggregate metrics, deterministic findings, citations, disclosures, and limitations under a
  new immutable snapshot ID. Optional aggregate CSV is rendered only from the stored snapshot,
  with owner/reviewer authorization and durable generation/download audit events; raw harmful
  content, authors, and item-level bulk rows are excluded.

- **Milestone 3 — collection and canonical processing (B-S7–B-S12, B-S24).** Collection runs
  and background jobs as an explicit state machine: transactional claims with leases,
  `FOR UPDATE SKIP LOCKED` so concurrent workers never take the same job, checkpoint-before-
  enqueue so a stage never starts against output that was not stored, bounded exponential
  backoff with jitter, dead-lettering when the retry budget is spent, and lease recovery that
  respects the attempts a crashed worker already consumed. Administrator `GET`/`POST
  /v1/admin/runs` and `GET /v1/admin/runs/{id}` with source, window, and item-cap validation;
  a redelivered dispatch answers `200` with the existing run rather than `201` with a second.
- One canonical `ContentItem` contract for news, social, user submissions, and open datapacks,
  with discover/fetch/canonicalize/checkpoint/health-check responsibilities, an adapter
  registry that refuses to serve a live source with a fixture adapter, a reusable adapter
  contract test suite, and a deterministic fixture adapter proving the pipeline end to end
  offline and idempotently.
- Reviewed, versioned source and seed configuration in `config/`, projected into
  `sources` and `source_seed_entries` by `amanah-etl sync-config`. The Markdown seed registry
  is never parsed at runtime; an entry runs only when it is `approved` and inside the
  English-only MVP language scope.
- Bounded news ingestion from the reviewed RSS/Atom allowlist in `docs/news-rss-sources.md`,
  with per-feed topical relevance filters as configuration, metadata-and-excerpt storage only,
  `content:encoded` deliberately never read, and database-enforced deduplication on canonical
  URL and on normalized publisher/headline. An unreachable feed is a coverage warning and a
  gap, never a zero.
- `GET /v1/news` reworked as the context news stream (reconciliation G5): `window`, `applied`,
  `coverage`, `data_mode`, `next_cursor`, and publisher-metadata items with no hate label,
  score, severity, or review state — the projection it reads has no column for one.
- Manifest-validated open-datapack import: provider, dataset name/version, landing page,
  licence, permitted uses, retrieval time, SHA-256, schema mapping, and approval all verified
  *before* any content write. Rows map to source kind `open_datapack` and public source and
  platform `N/A` while keeping full lineage, and original dataset labels are stored as dataset
  annotations, never as Amanah predictions.
- Bounded YouTube ingestion through the official Data API only: approved query and seed modes,
  quota deferral as a coverage gap, disabled comments and omitted replies recorded rather than
  read as silence, pagination checkpoints, per-seed and per-video caps, sampling stratum on
  every item, and no author identifier retained.
- Safe user-URL retrieval: HTTP(S) only, no credentials, port allowlist, every resolved address
  checked against the private and reserved ranges, each redirect hop re-validated, byte budget
  and content-type allowlist, metadata-and-excerpt extraction with no shell or browser, and
  typed analyzed/duplicate/unsupported/inaccessible/rejected/failed outcomes.
- Deterministic normalization and deduplication: Unicode composition folded and invisible
  matcher-evasion characters removed while case, punctuation, emoji, quotation marks, and
  stylised Unicode are preserved exactly. Stored text is never masked or profanity-filtered
  (B-S12.9). Permitted original text is encrypted at rest with AES-256-GCM; with no key
  configured it is not retained at all rather than written as plaintext into a column the
  schema calls ciphertext.
- Bounded historical backfill (~5 years) as resumable windowed runs through the same pipeline,
  with `backfill` run provenance, window keys derived from the window rather than the launch
  time, and per-window coverage so a sparse historical bucket renders as a gap.
- Migration `0004_collection_pipeline`: `background_jobs`, lease/retry/dead-letter columns on
  `collection_runs`, news dedupe keys and normalization columns on `content_items`, and the
  `authenticated_news`, `authenticated_collection_runs`, and `authenticated_background_jobs`
  projections. Base tables stay ungranted; the admin projections carry an administrator
  predicate and have no column for a queue payload, a checkpoint, or a lease owner.
- Spec §14.1 amended additively with the `background_job` table and its uniqueness rules, and
  §17.1 with lease semantics.

### Fixed

- `Database.session_for` now republishes the verified caller on every transaction rather than
  once per request. `SET LOCAL` lasts only as long as its transaction, so a service that
  committed mid-request continued on an anonymous connection and read nothing through the
  authenticated projections.
- URL validation refuses IPv6 hosts correctly. `urlsplit` strips the brackets, so the rebuilt
  URL read as `http://::1/`, which re-parses to *no host at all* and passed the
  private-destination check.
- URL validation refuses the legacy IP spellings — `2130706433`, `0177.0.0.1`, `127.1` — which
  connect to `127.0.0.1` without ever looking like a dotted quad.


- Collection-run and background-job state machines (Milestone 3, B-S7). Explicit valid
  transitions for `queued`, `running`, `retry_wait`, `succeeded`, `failed`,
  `policy_blocked`, and `cancelled`; idempotency keys derived from the work rather than
  the delivery; transactional claims with leases and `FOR UPDATE SKIP LOCKED`; lease
  recovery that respects the retry budget; bounded exponential backoff with full jitter;
  dead-letter state; and `GET/POST /v1/admin/runs` and `GET /v1/admin/runs/{id}` with
  source, window, and item-cap validation, administrator-only at both the route and the
  projection.
- The canonical adapter contract and a deterministic fixture adapter (B-S8). One
  `CanonicalContentItem` for news, social, user submissions, and datapack rows; discover,
  fetch, canonicalize, checkpoint, and health-check responsibilities; an adapter registry
  that refuses to serve a live source with a fixture adapter; a reusable contract test
  suite every future adapter inherits; and an end-to-end fixture run proving idempotent
  re-execution.
- Reviewed, versioned source and seed configuration in `config/` (B-S8.9, B-S8.10). The
  seed registry and the RSS allowlist are never parsed at runtime: an entry runs only
  after review into validated YAML with a stable `registry_key`, `config_version`,
  approval, query family and purpose, sampling stratum, language, and cap.
- Bounded news ingestion from the reviewed RSS/Atom allowlist (B-S9), with `defusedxml`
  parsing, per-feed topical relevance filters applied through configuration, metadata and
  a short permitted excerpt only, and database-checked canonical-URL and
  publisher/headline deduplication. An unreachable feed is a coverage gap, never a zero.
- `GET /v1/news` reworked as the context news stream (B-S9.8, reconciliation G5):
  `window`, `applied`, `coverage`, `data_mode`, `next_cursor`, and publisher-metadata
  items with no hate label, score, severity, or review state. The projection behind it has
  no column for one.
- Manifest-validated open-datapack import (B-S9A). Provider, dataset name and version,
  landing page, licence, permitted uses, retrieval time, SHA-256, schema mapping, and
  approval are all verified before any content write; rows map to source kind
  `open_datapack` and public `N/A` while keeping their lineage; original dataset labels
  are stored as dataset annotations and never as Amanah predictions.
- Bounded YouTube ingestion through the official Data API only (B-S10), with approved
  registry-backed seed and query modes, quota deferral as a coverage gap, disabled
  comments and omitted replies recorded rather than read as silence, checkpointed
  pagination, per-seed and per-video caps, and the English-only MVP language gate.
- Safe user-URL retrieval (B-S11): scheme, credential, and port validation; every resolved
  address checked against private, loopback, link-local, and reserved ranges; legacy
  decimal and octal IP spellings parsed as addresses; manual redirect following with
  re-validation at every hop; connect/read/total timeouts, byte budgets, and a
  content-type allowlist; and typed analyzed/duplicate/unsupported/inaccessible/rejected/
  failed outcomes.
- Normalization and deduplication (B-S12). Unicode NFC with invisible-character and
  bidirectional-control removal that preserves case, punctuation, emoji, quotation marks,
  and identity terms; bounded source-aware context; exact content hashes; canonical URL and
  dedupe keys; versioned normalization; and retry-idempotent upserts. Stored text is never
  masked, censored, or profanity-filtered.
- AES-256-GCM encryption of permitted original text at rest. With no key configured the
  original is not retained at all rather than written as plaintext into a column the schema
  calls ciphertext.
- Bounded historical backfill (B-S24): resumable windowed runs through the existing
  canonical pipeline, keyed on the window so a resumed backfill skips what already
  succeeded, provenanced as `backfill` rather than `scheduled`, with per-window coverage so
  a sparse historical window renders as a gap and never as a real zero.
- `amanah-etl` with `run`, `backfill`, and `sync-config` subcommands, plus `--dry-run`.

### Changed

- `GET /v1/news` no longer returns `CursorPage[ItemSummary]`. It returns the context news
  stream agreed in `docs/news-rss-sources.md`; classified news *item cards* remain on
  `/v1/items`. OpenAPI and the contract tests moved with it (reconciliation G5).
- Request-scoped database sessions re-publish the verified caller on every transaction
  rather than once per request, so a service that commits mid-request keeps its identity
  and the owner and role predicates still have someone to evaluate.
- `spec.md` section 14.1 records the `background_job` table and the lease, retry, and cap
  columns on `collection_run`; section 14.6 records the job idempotency key and the two
  news dedupe keys.

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

