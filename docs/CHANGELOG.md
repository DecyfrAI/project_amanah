# Changelog

All notable project changes are documented here using the Keep a Changelog structure.

## [Unreleased]

### Added

- **Live YouTube demo catalogue activation (B-S10).** Five product-owner-approved
  video IDs from the project seed registry now run through the official Data API:
  four enriched discussion seeds and one counterspeech/control seed. Every seed
  was live-preflighted, is capped at 100 items, carries stable sampling
  provenance, and remains disabled at runtime when `YOUTUBE_API_KEY` is missing.
  The adapter applies the remaining run cap and the per-seed cap before comment
  pagination, preventing a small dry run from spending quota on discarded rows.
  Adding a key does not authorize arbitrary videos, queries, or scraping, and
  this purposive hackathon sample cannot support YouTube-wide prevalence claims.

- **Authenticated image upload (B-S28).** `POST /v1/image-uploads` takes one multipart image,
  and `POST /v1/image-classifications` now accepts either a catalogue `example_id` or an
  `upload_id` — exactly one, enforced by a check constraint so "whose image is this?" always
  has an answer. Splitting upload from classification means a model failure never costs the
  person their file.
  - Nothing the client sends is trusted: the 5 MB cap is enforced while reading rather than
    from the declared length, the format is decided by decoding the bytes rather than from the
    filename or content type, and the stored object is a **re-encode**, so EXIF, GPS, XMP, and
    any trailing non-image payload do not survive. A file that is both a valid PNG and a valid
    script stops being the second one.
  - The storage key is generated server-side (`user-images/<owner>/<uuid>.<ext>`); nothing the
    caller sent contributes to it. PostgreSQL holds owner, path, digest, MIME, size,
    dimensions, and retention — never bytes, and never the original filename.
  - Migration `0008_user_image_uploads` adds `image_uploads` with RLS forced: anonymous reaches
    nothing, an upload is readable by its owner alone (not by reviewers — a colleague's private
    file is not their remit), and an administrator may read and delete so retention is operable.
    The projection carries no storage path.
  - Uploaded pixels are a new transfer class, `user_submitted_media`, refused unless
    `ALLOW_THIRD_PARTY_CONTENT_INFERENCE` is set. The fixture flag cannot bypass it: a caller
    must not be able to relabel someone's upload as this product's own material.

### Removed

- **PA-05 discussion attachments are descoped** by product-owner decision. Text notes and
  first-party chart captures remain on both viewer snapshots and machine-generated insights.
  Arbitrary uploads into a shared thread were excluded for safety rather than time — they
  would need malware scanning, safe download handling, and per-attachment authorization, and
  ADR 0004 refused a screenshot board because it would redistribute the material this product
  exists to measure. Recorded in `completion-guide.md`, `apps/web/todo.md`, and the README so
  the absence reads as a decision.

### Fixed

- **The migration history had branched into three heads,** so `alembic upgrade head`
  refused to run against any fresh database — including Render's pre-deploy step, which
  would have failed on the first real deployment. `0007_merge_milestone_heads` rejoins the
  three branches that grew out of `0004`; it carries no DDL, only graph bookkeeping.
- **Application and database clocks are no longer compared against each other.** Five
  sites wrote `datetime.now(UTC)` into a column whose partner defaults to `now()`
  server-side under a check constraint requiring one to follow the other, so settling a
  collection run, retracting a discussion note, or resolving a dispute raised an
  `IntegrityError` whenever the database clock ran microseconds ahead. `JobService.claim_next`
  had the same fault in reverse — it compared a server-defaulted `available_at` against this
  process's clock, so a freshly enqueued job was invisible and the queue appeared empty.
- **Arrays of Postgres enums no longer deserialize into single characters.** psycopg
  returned `hate_type[]` as the raw literal `'{derogation}'`, which SQLAlchemy then split
  per character, so `HateType('{')` would have raised on the image catalogue the moment
  Storage was configured. The enum type is now registered on every pooled connection, in
  the application engine and the test engine alike.
- **Supabase Storage is reached through the provider's own API.** Signed URLs were minted
  from a homegrown HMAC over the content-encryption key and pointed at Supabase's
  `authenticated` route, which understands neither that signature nor query-string
  credentials; object reads presented `SUPABASE_JWT_SECRET`, a token-*verification* secret,
  as though it were an access token. Both are replaced by the official signing endpoint and
  a dedicated server-only `SUPABASE_STORAGE_SECRET_KEY`. Absent that key, the catalogue reports
  itself unavailable instead of serving links that would fail.

### Added

- **Real news ingestion.** 32 articles from four reviewed publishers (BBC News, The
  Guardian, Al Jazeera English, Tell MAMA) are ingested through the canonical pipeline.
  The topical filter rejected 53 off-topic items on the first BBC run, and repeating a run
  deduplicated 5 of 12 discovered items rather than storing them twice.
- Item detail (`F-S8`) at `/app/explorer/:itemId`: the full model disclosure — score, model,
  prompt and taxonomy versions, inference time, rationale — beside the sampling limitation,
  with dataset provenance for datapack rows and no person-level field anywhere.
- Contributions history (`F-S11`) at `/app/contributions`: one owner-scoped view across URL
  submissions, disputes, and prepared reports. A prepared report reads as *prepared* until
  the owner records that they filed it themselves.
- The database test suite creates the Supabase roles (`anon`, `authenticated`) its RLS
  policies grant to, so it runs on any plain Postgres. The 401 tests that had always been
  skipped now execute: **937 pass, none skipped.**

- **Frontend/backend integration — the demo is wired end to end.** Supabase Auth
  replaces the fixture session: `SessionProvider` restores a real session before any
  protected route renders, every `live-provider.ts` request carries the access token as
  a bearer header, a `401` clears the spent session so the guard returns to login, and a
  `403` stays a permission denial without signing the person out. A new `demo` data mode
  routes product data to the live API with no catch-and-fallback, so a live failure stays
  a visible failure and never becomes fixture data.
- `apps/web/src/api/wire.ts`: Zod schemas mirroring the backend Pydantic contracts. Live
  responses are validated against those before being mapped into view models, which
  closes reconciliation gaps G1–G5, G7, G10, and the read half of G8.
- Assisted platform reporting through the reviewed policy catalogue (`PolicyReportFlow`):
  candidates with their official links, versions, and last-reviewed dates; explicit
  policy-version confirmation before saving; persistence through `POST /v1/prepared-reports`;
  and outcome recording through `PATCH`. Nothing in the flow can submit a report.
- Research-report snapshots (`ResearchReportPanel`): real creation through
  `POST /v1/research-reports`, the stored snapshot rendered with its scope, coverage,
  figures, citations, methodology version, and limitations, aggregate CSV download, and
  print styles for Save as PDF. The inert scope form and illustrative snapshot list are gone.
- Vendor bundle splitting: the entry chunk is ~252 kB, under Vite's 500 kB warning (F-S21.6).
- Security headers and immutable asset caching in `netlify.toml`.
- A reviewer-focused root `README.md` (PA-06).
- Backend `B-S28`: authenticated multipart image upload, recorded as **not implemented**.

### Changed

- **Media display is now controlled by the viewer (ADR 0010, amending ADR 0007).** Images
  are visible by default on authenticated surfaces; "Blur media by default" is an opt-in
  preference persisted on the profile through `PATCH /v1/me`, applied across Explorer,
  Review, Insights, and Reports at once and immediately, with an accessible per-image
  Show/Hide override on every image. Blur is a display treatment only — it changes no
  authorization, ownership check, RLS rule, or signed-URL handling, and text redaction is
  untouched. `spec.md` §18 updated.
- The nine-second post-login hold is gone. Navigation follows the real authentication and
  request lifecycle, with a bounded 60-second request timeout so a dead API ends in a
  retryable error rather than an infinite loader (PA-03).
- Insight detail pages carry a `View all insights` action and a success notice after
  creation, and a second click while the create is in flight no longer writes a duplicate
  (PA-04).
- The discussion composer respects the server's `can_participate`, so an uninvited reader
  is not offered a control whose every use would be refused (ADR 0004).

### Removed

- The unscoped Image Evidence section on the Insights list, with its hook and component.
  It requested an unfiltered Explorer page and showed every image it found, none of which
  was tied to the insights on the page (PA-02).

- **Milestone 7 — scheduling, resilience, observability, CI, and deployment readiness
  (B-S21–B-S23).** Scheduled and manual eight-hour collection now share the validated,
  checkpointed `amanah-etl run-from-env` command and constrain source, stable seed/config,
  datapack manifest ID, cap, concurrency, fixture mode, and redacted artifacts. Request/run/job
  correlation, sensitive-field redaction, API limits with `Retry-After`, safe CI and AI evals,
  security gates, Render configuration, smoke checks, threat model, rollback, and operations
  runbooks complete the reproducible deployment path without live-provider calls in CI.

### Added

- **Milestone 5 — authenticated contributions and human review (B-S16 to B-S18, B-S27).**
  `POST /v1/submissions` records one public URL as `processing` and queues the same canonical
  pipeline collected content uses; the resolver-free half of the SSRF check runs in the request
  so a private literal, an unsafe port, or credentials in the URL are refused before a row
  exists, while `SafeUrlFetcher` still re-resolves and re-validates every redirect hop at
  retrieval, which remains the security boundary. Idempotency is the natural key
  `(user, canonical URL)`, so a resubmission answers `200` with the existing record; a URL that
  already produced an item is recorded as `duplicate` and queues nothing.
- A `user_submission` adapter that discovers the queue of pending submissions, retrieves each
  through the safe fetcher, settles the ones with no readable page as `unsupported`,
  `inaccessible`, `rejected`, or `failed`, and canonicalizes the rest into metadata-only items.
  The pipeline links the stored item back to its submission, turning "processing" in a user's
  history into a link to the result.
- `GET /v1/me/contributions`: one cursor-paginated history across submissions, disputes, and
  prepared reports, built as a `UNION ALL` over the three owner-scoped projections, plus
  `GET /v1/me/contributions/{id}/events` for the appended timeline. Every timeline line is
  composed from controlled vocabulary, so no provider text, source wording, or reviewer note
  can reach one.
- Classification disputes: one open dispute per user and item, an idempotent retry returning the
  existing record, and a shared review task when two people dispute the same prediction. A
  dispute moves the item's *effective* review state and never edits the prediction.
- The reviewer workflow: `GET /v1/review/tasks` (highest priority, oldest first),
  `POST …/claim` as a conditional update so exactly one reviewer wins a race,
  `POST …/decisions` appending to `review_events`, effective-label projection updates, a
  user-safe resolution on every attached dispute's timeline, and lease release for abandoned
  claims. Approved corrections are flagged `is_training_candidate` into a pool nothing in this
  service reads — the absence of a consumer is the quarantine.
- Assisted platform reporting without any external side effect: a reviewed catalogue in
  `config/platform-policies.yml`, deterministic candidate matching behind a `PolicyMatcher`
  seam (a Gemini-backed ranker implements the same contract when B-S13 lands), possible-match
  language that never claims a violation, mandatory confirmation of a policy *and* its version,
  a stale version reported as a conflict rather than substituted, and one prepared report per
  user, item, and platform. FR-TOS-010: a platform with no reporting form gets an email-style
  draft addressed only to the reviewer-approved allow-listed address in the catalogue — a caller
  has no field in which to name a recipient, and nothing is ever sent.
- ADR 0004 insight discussion: `snapshot_insights` freeze a claim with its numerator,
  denominator, window, sources, and Explorer filter state, and a trigger refuses any later
  edit. Invite-only participation through `discussion_participants`; notes attach to an insight
  and there is no table for a thread without one; `useful`/`needs_context` reactions count per
  post with one row per person and no per-author aggregate anywhere; retraction replaces the
  body and detaches the capture while leaving the row in place. Captures are first-party
  renderings only — both the image path and the Explorer link must be site-relative, and
  `//host` is rejected along with absolute URLs.
- `PATCH /v1/me` persists display name, onboarding state, and content-safety preferences.
  `GET /v1/me` now reports them alongside the verified identity; the effective role still comes
  from the token, never from the stored row, so a stale row cannot grant access.
- Per-user rate limits on submissions, disputes, prepared reports, and discussion notes,
  counted from the rows each action already writes so two API instances cannot each allow a
  full quota. A refusal returns `429` with `Retry-After`.
- Migration `0005`: reviewer and discussion projections, the FR-TOS-010 recipient columns with
  constraints keeping form and email platforms consistent, five new tables with row-level
  security enabled and forced, and the snapshot immutability trigger. Migration `0006` moves
  the channel-completeness check to publication, so a draft catalogue entry a reviewer has not
  finished can still exist while nothing incomplete can be offered to a user.

### Fixed

- `review_events.corrected_labels` wrote a JSON `null` rather than SQL `NULL` for a decision
  with no labels, which the `corrected_labels_match_decision` check constraint read as "labels
  present" — every confirmation, rejection, and needs-context decision would have failed to
  insert. The column now uses `JSONB(none_as_null=True)`.

- **Milestone 6 — governed resources and immutable research reports (B-S19–B-S20).**
  Reviewer/admin resource creation, revision, explicit human-confirmed publication, archive,
  and append-only audit history; published wording changes return to draft and only reviewed
  entries reach authenticated base-role readers. Authenticated filter-scoped research-report
  generation now freezes data and methodology versions, coverage, denominators, selected
  aggregate metrics, deterministic findings, citations, disclosures, and limitations under a
  new immutable snapshot ID. Optional aggregate CSV is rendered only from the stored snapshot,
  with owner/reviewer authorization and durable generation/download audit events; raw harmful
  content, authors, and item-level bulk rows are excluded.

### Added

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
