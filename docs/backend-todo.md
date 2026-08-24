# Project Amanah — Backend, ML, and DevOps Todo Checklist

**Source of truth:** [`spec.md`](./spec.md)  
**Candidate source catalog:** [`PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`](./PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md) — review input only  
**Implementation plan:** [`backend-implementation-plan.md`](./backend-implementation-plan.md)  
**Frontend reconciliation:** [`frontend-backend-reconciliation.md`](./frontend-backend-reconciliation.md) — gaps G1–G11 and the 23 Aug 2026 change requests; B-S24–B-S27 originate there  
**Agent rules:** [`AGENTS.md`](./AGENTS.md) and applicable files under [`rules/`](./rules/)  
**Tracks:** Backend, ML, DevOps

Use this checklist in Step ID order even though it is grouped by track. Respect dependencies listed in the implementation plan. A parent step is complete only when its child checks and applicable cross-cutting gates are complete.

## TRACK: backend

### Milestone 1 — Backend foundation and contracts

- [x] **B-S1 — Audit and scaffold the FastAPI service**
  - [x] **B-S1.1** Read `spec.md`, `AGENTS.md`, and applicable general/backend/testing/security/documentation rules.
  - [x] **B-S1.2** Inventory existing backend files, dependencies, scripts, and user changes.
  - [x] **B-S1.3** Establish/reconcile the uv-managed FastAPI package and application factory.
  - [x] **B-S1.4** Configure pinned dependencies and scripts for dev, lint, type check, format, and tests.
  - [x] **B-S1.5** Add a meaningful import/startup smoke test.
  - [x] **B-S1.6** Document and verify local backend commands without secret values.

- [x] **B-S2 — Define contract-first domain and API schemas**
  - [x] **B-S2.1** Add controlled enums for source, content, relevance, stance, hate type, severity, confidence, review, contribution, and job states.
  - [x] **B-S2.2** Define authenticated-safe dashboard/item/resource models, common response metadata, and bearer-auth requirements for every `/v1` product operation.
  - [x] **B-S2.3** Define cursor pagination and validated filter/sort models.
  - [x] **B-S2.4** Define the exact safe error envelope with request ID and retryability.
  - [x] **B-S2.5** Standardize UTC timestamps, `snake_case` JSON, nullable semantics, and additive v1 evolution.
  - [x] **B-S2.6** Test invalid enums, unsupported filters/sorts, rate denominator requirements, and safe error serialization.
  - [x] **B-S2.7** Include `open_datapack` source kind and controlled `not_applicable`/`N/A` public source value.

- [x] **B-S4 — Add configuration, health, errors, and authentication boundary**
  - [x] **B-S4.1** Validate core settings at startup and model optional connector configuration explicitly.
  - [x] **B-S4.2** Implement `/healthz` and dependency-aware `/readyz` without secrets/internal versions. Readiness currently checks that a database target is configured; the live connectivity probe lands with the database layer in B-S3.
  - [x] **B-S4.3** Add request IDs and centralized safe exception-to-error-envelope mapping.
  - [x] **B-S4.4** Verify Supabase JWTs server-side and add authenticated-user/reviewer/admin dependencies plus a consistent anonymous `401` path.
  - [x] **B-S4.5** Add reusable resource-ownership checks for contributions and reports.
  - [x] **B-S4.6** Log authentication/authorization outcomes without tokens or harmful content.
  - [x] **B-S4.7** Apply authenticated-user dependency by default to `/v1` and test missing/invalid/expired tokens, role denial, ownership denial, degraded readiness, and safe errors.

### Milestone 2 — Relational storage and authenticated read API

- [x] **B-S3 — Create the core database schema and RLS foundation**
  - [x] **B-S3.1** Read the database plan/rules and confirm explicit authorization before changing migration files.
  - [x] **B-S3.2** Add core source, run, content, prediction, metric, user, contribution, dispute, review, policy, resource, and report tables.
  - [x] **B-S3.3** Use UUID keys, UTC timestamps, explicit enums, foreign keys, and documented check/unique constraints.
  - [x] **B-S3.4** Add only query-driven indexes and verify expected access paths.
  - [x] **B-S3.5** Make review/contribution decisions append-only and ready report snapshots immutable.
  - [x] **B-S3.6** Add authenticated-safe projections that exclude encrypted/raw content and author identifiers.
  - [x] **B-S3.7** Deny anonymous access to every product table/view/function/storage object and add authenticated base-role, owner, reviewer, and admin RLS boundaries.
  - [x] **B-S3.8** Test empty-database migrations, constraints, negative RLS cases, and supported migration compatibility.
  - [x] **B-S3.9** Add dataset package and import-run tables plus package/version/license/file-hash/schema-mapping/row provenance.
  - [x] **B-S3.10** Map datapack items to the controlled `N/A` source row while preserving separate dataset provenance.
  - [x] **B-S3.11** Add source-seed configuration storage constrained by stable registry key/config version with approval, language, cap, query purpose, and sampling stratum.

- [x] **B-S5 — Implement authenticated dashboard and item read APIs**
  - [x] **B-S5.1** Implement parameterized repositories for dashboard metrics, headlines, news, item lists, and item detail.
  - [x] **B-S5.2** Support all validated authenticated filters and stable documented sorts.
  - [x] **B-S5.3** Implement cursor pagination with stable secondary ordering.
  - [x] **B-S5.4** Return numerator, denominator, scope, window, coverage, and data mode for every rate.
  - [x] **B-S5.5** Preserve missing buckets as gaps and expose stale/partial warnings.
  - [x] **B-S5.6** Exclude raw fields, author identifiers, and unauthorized evidence.
  - [x] **B-S5.7** Test filters, cursors, unsupported inputs, empty data, redaction, representative query plans, and anonymous denial for every read route.
  - [x] **B-S5.8** Add a distinct Dataset filter and return dataset provider/name/version separately from source/platform `N/A`.

- [x] **B-S6 — Implement authenticated methodology, resources, and connection-status reads**
  - [x] **B-S6.1** Implement authenticated methodology disclosures for sampling, taxonomy, models, coverage, and limitations.
  - [x] **B-S6.2** Implement authenticated base-role reads for published resource entries only.
  - [x] **B-S6.3** Return resource organization, country/scope, category, summary, URL, and last-reviewed date.
  - [x] **B-S6.4** Implement safe connector state with purpose, status, last success/check, and safe warnings.
  - [x] **B-S6.5** Ensure connector responses never include keys, connection strings, or raw provider failures.
  - [x] **B-S6.6** Add caching and invalidation only where justified. *(None added: the four
    reads are single indexed queries or static prose, and a cache would introduce staleness
    the coverage disclosure would then have to describe. Revisit if a read shows up hot.)*
  - [x] **B-S6.7** Test anonymous denial, unpublished-resource denial, and secret-free methodology/connector serialization.

### Milestone 3 — Collection and canonical processing

- [x] **B-S7 — Implement collection-run and background-job state machines**
  - [x] **B-S7.1** Implement valid transitions for queued, running, retry_wait, succeeded, failed, policy_blocked, and cancelled.
  - [x] **B-S7.2** Persist idempotency/natural keys for runs and jobs.
  - [x] **B-S7.3** Claim jobs transactionally with leases and recover expired claims safely.
  - [x] **B-S7.4** Checkpoint stage output before enqueueing the next stage.
  - [x] **B-S7.5** Store bounded retry metadata, next-run time, dead-letter state, and safe errors.
  - [x] **B-S7.6** Add admin run create/read endpoints with source/window/item-cap validation.
  - [x] **B-S7.7** Test duplicate delivery, concurrency, invalid transitions, lease loss, retry, and partial failure.

- [x] **B-S8 — Implement the canonical adapter contract and fixture adapter**
  - [x] **B-S8.1** Define discover, fetch, canonicalize, checkpoint, and health-check responsibilities.
  - [x] **B-S8.2** Define one canonical `ContentItem` for news, social, and user-submitted sources.
  - [x] **B-S8.3** Implement deterministic synthetic/redacted fixture discovery and processing.
  - [x] **B-S8.4** Mark fixture records and runs explicitly through storage/API projections.
  - [x] **B-S8.5** Persist adapter/config versions, cursors, and coverage counts.
  - [x] **B-S8.6** Add a reusable adapter contract test suite.
  - [x] **B-S8.7** Add an end-to-end fixture run that proves idempotent re-execution.
  - [x] **B-S8.8** Extend canonical content for open datapacks with source/platform `N/A` and separate package/import/row provenance.
  - [x] **B-S8.9** Define approved seed configuration with stable registry key, query family/purpose, sampling stratum, language, item cap, approval, and config version.
  - [x] **B-S8.10** Keep `PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md` as human reference input; never parse it or auto-activate its entries at runtime.

- [x] **B-S9 — Implement bounded news ingestion**
  - [x] **B-S9.1** Select/configure GDELT and/or reviewed RSS without embedding credentials.
  - [x] **B-S9.2** Store headline, publisher, canonical URL, permitted excerpt, publication/retrieval time, language, scope, and explicit location only.
  - [x] **B-S9.3** Avoid full-article storage, paywall bypass, and unauthorized scraping.
  - [x] **B-S9.4** Deduplicate by canonical URL and normalized provider/headline, checking the database before insert; a duplicate links to the existing row instead of writing a new one.
  - [x] **B-S9.5** Add timeouts, result/byte limits, rate handling, checkpoints, and coverage warnings.
  - [x] **B-S9.6** Test malformed, partial, duplicate, paginated, rate-limited, and outage responses at the HTTP boundary.
  - [x] **B-S9.7** Use [`news-rss-sources.md`](./news-rss-sources.md) as the reviewed RSS/Atom allowlist and apply its per-feed topical relevance filters (keep religion/hate-crime/public-affairs coverage; drop sport/celebrity) through configuration, never treating Muslim-related vocabulary as a harm signal. Do not add feeds it rejected or invent replacements.
  - [x] **B-S9.8** Serve `GET /v1/news` as the context news stream contract from that hand-off (`window`, `applied`, `coverage`, `data_mode`, `next_cursor`, publisher-metadata items with no hate label, score, or review state), reworking the Milestone 2 items-shaped route with OpenAPI and contract tests updated together (reconciliation G5).
  - [x] **B-S9.9** Keep English-only for P0, scope to Canada/US/UK plus clearly global religion or hate-crime reporting, and never attach a classification to an ingested article.

- [x] **B-S9A — Implement reviewed open-datapack ingestion**
  - [x] **B-S9A.1** Define a reviewed manifest for provider, dataset name/version, landing page, license, permitted uses, retrieval time, file hash, schema mapping, and approval.
  - [x] **B-S9A.2** Import reviewed UTF-8 CSV and JSONL files without adding an ungoverned download crawler.
  - [x] **B-S9A.3** Validate manifest, approval, license, SHA-256, encoding, required columns, schema mapping, and stable row identity before content writes.
  - [x] **B-S9A.4** Map every row to source kind `open_datapack` and public source/platform `N/A`.
  - [x] **B-S9A.5** Persist provider/name/version/license/file/import/row provenance separately.
  - [x] **B-S9A.6** Store original dataset labels as dataset annotations only, never as Amanah predictions/reviews.
  - [x] **B-S9A.7** Enforce `(dataset_package_id, dataset_row_id)` idempotency and cross-package collision safety.
  - [x] **B-S9A.8** Stream/batch within configured limits and record imported/skipped/error counts without harmful raw text in logs.
  - [x] **B-S9A.9** Test valid CSV/JSONL, duplicate/cross-package rows, malformed rows, wrong hash, bad encoding, unapproved license, retry, and `N/A` projection.

- [x] **B-S10 — Implement bounded YouTube ingestion**
  - [x] **B-S10.1** Enable the adapter only when an API key and approved configuration are present.
  - [x] **B-S10.2** Implement official query and seed-video discovery modes.
  - [x] **B-S10.3** Retrieve bounded video metadata, top-level comments, and replies through official APIs.
  - [x] **B-S10.4** Persist source IDs, query purpose, window, timestamps, and adapter/config version.
  - [x] **B-S10.5** Record disabled comments, deleted/omitted replies, quota deferral, and coverage gaps.
  - [x] **B-S10.6** Checkpoint pagination and enforce query/video/comment caps.
  - [x] **B-S10.7** Prohibit scraping or unsupported transcript retrieval.
  - [x] **B-S10.8** Test pagination, quota, disabled comments, partial replies, deletion, retry, and missing key.
  - [x] **B-S10.9** Project only approved registry seed/query entries into runtime configuration and persist their stable provenance.
  - [x] **B-S10.10** Keep enriched, boundary/control, and ordinary-monitoring strata separate and enforce the English-only MVP language gate.
  - [x] **B-S10.11** Test unknown/unapproved registry keys, unavailable seeds as coverage gaps, cap enforcement, and stratum provenance.

- [x] **B-S11 — Implement safe user-URL retrieval**
  - [x] **B-S11.1** Accept and normalize only public HTTP(S) URLs.
  - [x] **B-S11.2** Reject credentials, unsafe ports, private/reserved/link-local targets, and prohibited schemes before network access.
  - [x] **B-S11.3** Resolve DNS safely, revalidate every redirect, and prevent DNS-rebinding/private-destination access.
  - [x] **B-S11.4** Enforce connect/read/total timeouts, redirect limits, byte limits, and content-type allowlists.
  - [x] **B-S11.5** Extract metadata/permitted excerpts only and never invoke a shell or general browser.
  - [x] **B-S11.6** Return explicit duplicate, unsupported, inaccessible, rejected, and failed states.
  - [x] **B-S11.7** Test localhost/IP encodings, redirects, oversized bodies, malformed content, paywalls, duplicates, and timeout behavior.

- [x] **B-S12 — Implement normalization and deduplication**
  - [x] **B-S12.1** Preserve permitted original/encrypted text separately from normalized/model text.
  - [x] **B-S12.2** Normalize Unicode and whitespace without destroying punctuation, emoji, quotes, identity terms, or stance context.
  - [x] **B-S12.3** Assemble bounded source-aware title/parent/root/caption context.
  - [x] **B-S12.4** Record language and explicit null/unavailable semantics.
  - [x] **B-S12.5** Implement canonical source/URL keys and exact content hashes.
  - [x] **B-S12.6** Version normalization and make content upserts retry-idempotent.
  - [x] **B-S12.7** Test Unicode, counterspeech, quotation, missing context, duplicate source IDs, canonical URLs, and repeat execution.
  - [x] **B-S12.8** Deduplicate datapack rows by dataset package/row identity without collapsing the same row ID across different packages.
  - [x] **B-S12.9** Never mask, censor, or profanity-filter stored original or normalized text: researchers need the exact wording. Redaction and blurring are display-layer (frontend) and report-snapshot (B-S20.3) concerns only.

- [x] **B-S24 — Implement bounded historical backfill (~5 years)**
  - [x] **B-S24.1** Backfill exclusively through the existing canonical pipeline and adapters; no new scraping path and no source outside approved configuration.
  - [x] **B-S24.2** Use reviewed open datapacks (B-S9A) as the primary historical source, with GDELT/RSS historical windows for news where provider terms permit.
  - [x] **B-S24.3** Use official-API YouTube seed/query discovery with explicit date windows and per-window item caps for historical social content.
  - [x] **B-S24.4** Run backfill as resumable windowed runs with checkpoints, distinct run provenance (`backfill` vs incremental), and the same strata/registry rules as live collection.
  - [x] **B-S24.5** Carry per-bucket coverage so sparse historical windows render as gaps or low-coverage, never as a real zero or a prevalence claim.
  - [x] **B-S24.6** Test window slicing, resume after interruption, dedupe against already-ingested content, cap enforcement, and coverage bucket provenance.

### Milestone 5 — Authenticated contributions and human review

- [x] **B-S16 — Implement URL submissions and contribution history**
  - [x] **B-S16.1** Add authenticated one-public-URL submission with server-side validation.
  - [x] **B-S16.2** Enforce idempotency and link canonical duplicates rather than reprocessing.
  - [x] **B-S16.3** Persist Processing before enqueueing safe retrieval/canonical processing.
  - [x] **B-S16.4** Append user-safe contribution events for every status transition.
  - [x] **B-S16.5** Support processing, analyzed, duplicate, unsupported, inaccessible, rejected, and failed.
  - [x] **B-S16.6** Return cursor-paginated contributions owned by the authenticated user only.
  - [x] **B-S16.7** Rate-limit submissions and test auth, ownership, idempotency, transition, and enqueue behavior. *(Limits are counted from the rows each action already writes, so two API instances cannot each allow a full quota.)*

- [x] **B-S17 — Implement disputes and reviewer decisions**
  - [x] **B-S17.1** Enforce one open dispute per user/item.
  - [x] **B-S17.2** Return/link the existing dispute on an idempotent duplicate request.
  - [x] **B-S17.3** Create prioritized review tasks without changing the original prediction.
  - [x] **B-S17.4** Implement reviewer claim, append-only decision, and history endpoints with leases and roles.
  - [x] **B-S17.5** Update effective-label projections from review events while preserving history.
  - [x] **B-S17.6** Append a user-safe resolution to the user’s contribution timeline.
  - [x] **B-S17.7** Quarantine approved corrections as training candidates; never auto-train. *(`review_events.is_training_candidate` has no consumer anywhere in the service; the absence of one is the quarantine.)*
  - [x] **B-S17.8** Test concurrent claims, invalid decisions, ownership, immutability, duplicate disputes, and final outcomes.

- [x] **B-S18 — Implement platform-policy assistance and prepared reports**
  - [x] **B-S18.1** Add at least one reviewer-approved official platform-policy fixture/catalog entry with version and review date.
  - [x] **B-S18.2** Return constrained candidate policy matches with uncertainty and official links. *(Deterministic matching behind a `PolicyMatcher` seam. Milestone 4 is not implemented, so no Gemini ranking yet; a model-backed ranker implements the same contract when B-S13 lands and the routes do not change.)*
  - [x] **B-S18.3** Require explicit user-selected/confirmed policy ID and version before saving.
  - [x] **B-S18.4** Persist evidence summary, suggested wording, item, platform, policy version, user, and creation time.
  - [x] **B-S18.5** Implement prepared/submitted/outcome state transitions without claiming platform receipt.
  - [x] **B-S18.6** Prohibit platform reporting API calls, arbitrary destinations, and automatic submission.
  - [x] **B-S18.7** Add per-user/item abuse controls and anti-brigading limits.
  - [x] **B-S18.8** Test stale policies, low confidence, confirmation, ownership, outcomes, and absence of external side effects.
  - [x] **B-S18.9** Use the policy-catalog flow for platforms with an official reporting form; for a platform without one, produce an email-style draft (subject, body, evidence summary) addressed only to a reviewer-approved allow-listed address, never auto-sent (FR-TOS-010, spec v2.2; matches the frontend `ReportDraft` contract's `to_kind` split).

- [x] **B-S27 — Implement insight snapshots, discussion, captures, and profile persistence (ADR 0004)**
  - [x] **B-S27.1** Implement `PATCH /v1/me` for profile/onboarding persistence (spec §13.2 already lists it; reconciliation G10). Pull this sub-item forward if frontend onboarding needs it before the rest of the step.
  - [x] **B-S27.2** Land the additive `spec.md` §13 amendment for insights/discussion/captures/viewer-post routes (reconciliation G6). *(Done 23 Aug 2026: spec v2.2.)*
  - [x] **B-S27.3** Implement `GET/POST /v1/insights` and `GET /v1/insights/{id}`: a snapshot freezes claim, numerator/denominator, metric, window, coverage, and the Explorer filter state at capture time. *(Built on a new `snapshot_insights` table, not `insight_snapshots` — the latter is the AI narrative cache keyed by filter/model/prompt version and holds no claim. Counts come from the client per ADR 0004, so this needed no B-S15.)*
  - [x] **B-S27.4** Implement discussion (`GET /v1/insights/{id}/discussion`, `POST …/discussion/posts`), reactions (`useful`/`needs_context` counts only, never author ranking), and retraction that replaces the body and removes the capture while leaving the row.
  - [x] **B-S27.5** Implement `POST /v1/captures` for first-party dashboard figure captures (alt text, filter hash, Explorer deep link) and `GET /v1/me/posts` scoped to the caller.
  - [x] **B-S27.6** Keep participation invite-only per ADR 0004, deny anonymous access everywhere, apply RLS ownership boundaries, and rate-limit posting.
  - [x] **B-S27.7** Test snapshot immutability, retraction semantics, reaction idempotency, ownership and anonymous denial, and that no person-level ranking or free-floating board exists.

### Milestone 6 — Research reports and curated resources

- [x] **B-S19 — Implement curated resource administration and governance** *(Done 23 Aug 2026.)*
  - [x] **B-S19.1** Add reviewer/admin create, update, publish, archive, and list operations.
  - [x] **B-S19.2** Validate HTTPS URL, organization, category, country/scope, summary, reviewer, and last-reviewed date.
  - [x] **B-S19.3** Implement draft, published, and archived lifecycle.
  - [x] **B-S19.4** Keep audit history and publish only reviewed entries.
  - [x] **B-S19.5** Keep unreviewed candidate content in draft; do not publish raw AI-generated descriptions.
  - [x] **B-S19.6** Test roles, validation, publication, archive, audit, anonymous denial, and authenticated base-role projection.

- [x] **B-S20 — Implement research-report snapshots and aggregate export** *(Done 23 Aug 2026.)*
  - [x] **B-S20.1** Validate authorized report filters and resolve the exact data/methodology versions.
  - [x] **B-S20.2** Freeze coverage, denominators, selected metrics/findings, and citation IDs.
  - [x] **B-S20.3** Apply redaction and exclude raw harmful content, authors, and item-level bulk data by default.
  - [x] **B-S20.4** Make ready snapshots immutable; regenerate under a new ID.
  - [x] **B-S20.5** Generate aggregate CSV from the stored snapshot if included in scope.
  - [x] **B-S20.6** Enforce owner/reviewer authorization and audit generation/download.
  - [x] **B-S20.7** Test filter/citation fidelity, immutability, redaction, CSV schema, and cross-user denial.

### Milestone 7 — Production resilience and observability

- [x] **B-S22 — Add production resilience and observability**
  - [x] **B-S22.1** Add structured redacted logs with request/run/job correlation.
  - [x] **B-S22.2** Add documented metrics for API, connector, Gemini, job, contribution, review, and report behavior.
  - [x] **B-S22.3** Apply explicit dependency timeouts and bounded transient retries with jitter.
  - [x] **B-S22.4** Add per-IP/user rate limits and correct `Retry-After` behavior.
  - [x] **B-S22.5** Preserve last-successful data with stale/partial coverage; never silently swap fixtures.
  - [x] **B-S22.6** Isolate connector/item failures and implement accurate health/readiness semantics.
  - [x] **B-S22.7** Test provider outages, quota exhaustion, Gemini deferral, DB failure, lease loss, partial extraction, and auth expiry.

## TRACK: ml

### Milestone 4 — AI classification and research insights

- [x] **B-S13 — Implement the controlled Gemini client**
  - [x] **B-S13.1** Read `rules/ml.md`, `rules/agentic.md`, security/testing rules, and the AI sections of `spec.md`.
  - [x] **B-S13.2** Configure Gemini model/key through validated server settings only.
  - [x] **B-S13.3** Add strict structured input/output schemas and a prompt/version registry.
  - [x] **B-S13.4** Add deterministic cache keys using content/data/model/prompt/taxonomy versions.
  - [x] **B-S13.5** Add timeouts, bounded retries, context/output caps, and per-run/daily token budgets.
  - [x] **B-S13.6** Enforce data-class/transfer authorization before constructing a request.
  - [x] **B-S13.7** Treat content as prompt-injection data and expose no arbitrary SQL/network/tools.
  - [x] **B-S13.8** Return typed success, deferred, policy-blocked, invalid-output, and provider-failure results.
  - [x] **B-S13.9** Test cache, schema failure, timeouts, budgets, prompt injection, and prohibited transfer.

- [x] **B-S14 — Implement staged classification and confidence**
  - [x] **B-S14.1** Separate relevance, stance, multi-label type, severity, narrative, score, rationale, and review need.
  - [x] **B-S14.2** Represent counterspeech/quotation and uncertainty explicitly.
  - [x] **B-S14.3** Map numeric scores to versioned configurable Low/Medium/High tiers.
  - [x] **B-S14.4** Mark default thresholds provisional until calibrated on a reviewed holdout. *(The version string itself carries `-provisional`, so the disclosure travels on every prediction row.)*
  - [x] **B-S14.5** Persist model, prompt, taxonomy, normalization, and inference versions without overwriting older predictions.
  - [x] **B-S14.6** Route low-confidence, uncertain, severe, invalid, and disagreement cases to review.
  - [x] **B-S14.7** Build a frozen licensed/synthetic/redacted evaluation set with benign Muslim, news, criticism, counterspeech, coded, ambiguous, and injection cases. *(`evals/registry/`, 22 synthetic samples, `classification.test.v1`.)*
  - [x] **B-S14.8** Report confusion/calibration/false-positive slices without inventing an accuracy claim. *(Per-slice reporting is declared in the eval definition; scoring real model output against it runs in the B-S23.5 workflow. No accuracy claim is made anywhere.)*

- [x] **B-S15 — Implement deterministic metrics and cached insights**
  - [x] **B-S15.1** Compute observed, relevant, likely-hate, reviewed, and confirmed counts outside Gemini.
  - [x] **B-S15.2** Compute the monitored-sample likely anti-Muslim rhetoric rate with numerator and denominator.
  - [x] **B-S15.3** Store coverage, gaps, filter version, and bucket provenance.
  - [x] **B-S15.4** Build bounded fact bundles with immutable IDs and exact filters.
  - [x] **B-S15.5** Require every Gemini quantitative claim/citation to validate against the fact bundle.
  - [x] **B-S15.6** Separate observed facts, interpretation, possible association, and unknowns; reject causal language.
  - [x] **B-S15.7** Cache by filter/data/model/prompt version and preserve deterministic results when AI fails.
  - [x] **B-S15.8** Test aggregation, missing coverage, citation/numeric fidelity, causal refusal, insufficient data, and cache behavior.
  - [x] **B-S15.9** Group by sampling stratum and prevent enriched seed, boundary/control, and ordinary-monitoring results from silently becoming a prevalence metric. *(`sampling_stratum` is part of a bucket's unique identity, so two strata cannot upsert onto one row.)*
  - [x] **B-S15.10** Refresh cached fact bundles and insights whenever an ETL run lands new data (the version-keyed cache from B-S15.7 makes this an invalidation, not a bypass), so each pull yields current insights. *(`data_version` holds the fact-bundle digest, so newly collected items change the key and miss the cache.)*

- [x] **B-S25 — Implement the grounded dashboard assistant (`POST /v1/assistant/query`)**
  - [x] **B-S25.1** Land the additive `spec.md` §13 amendment for this route (reconciliation G7). *(Done 23 Aug 2026: spec v2.2, product-owner approval.)*
  - [x] **B-S25.2** Accept the frontend `AssistantAskInput` contract: a question plus the exact dashboard filters, so the reply cannot describe a different sample.
  - [x] **B-S25.3** Answer only from stored fact bundles (B-S15) and methodology text through the controlled Gemini client; the model never computes a number or reaches the database.
  - [x] **B-S25.4** Return `answer`, typed citations for every quantitative claim, explicit limitations, and `grounded_in` (`figures`/`methodology`/`none`); an ungrounded question gets a typed refusal, not an invented answer.
  - [x] **B-S25.5** Support the shipped starter queries (rate, trend, coverage, a single item walk-through, current events, news-coincidence) and describe association as coincidence only, refusing causal phrasing. *(The bundle carries rate, counts, coverage, and gap facts; per-item walk-through answers from `/v1/items/{id}` rather than the assistant.)*
  - [x] **B-S25.6** Treat the question as untrusted prompt-injection input, apply the B-S13 budgets/caching, and rate-limit per user.
  - [x] **B-S25.7** Test citation fidelity, causal refusal, injection resistance, insufficient-data abstention, filter fidelity, budget exhaustion, and Gemini-unavailable degradation.

- [x] **B-S26 — Implement the image-evidence catalog and classification (ADR 0007)**
  - **Scope correction (24 Aug 2026):** B-S26 covers classification of an image *already in the reviewed catalogue*. Authenticated **user upload is not implemented**: no route accepts a multipart file, so the frontend picker has no live path and refuses visibly rather than pretending. Tracked as B-S28 below; see completion guide step 8.
  - [x] **B-S26.1** Land the additive `spec.md` §13 amendment for the image routes (reconciliation G8). *(Done 23 Aug 2026: spec v2.2 adds `GET /v1/image-examples` and `POST /v1/image-classifications`.)*
  - [x] **B-S26.2** Store image bytes in object storage only; Postgres holds path, sha256, mime, byte size, dataset annotation JSON, and prediction JSON. Never base64 in the database and never pixels across the browser API boundary.
  - [x] **B-S26.3** Serve the authenticated image-example catalog with manifest provenance and short-lived signed URLs.
  - [x] **B-S26.4** Classify images server-side through the controlled Gemini boundary using the staged taxonomy (relevance, stance, types, severity, narrative, score, tier, rationale, review requirement), keeping dataset annotations separate from Amanah predictions.
  - [x] **B-S26.5** Keep live image *ingestion* gated: Reddit stays disabled/fixture until Reddit-for-Researchers approval and credentials exist (spec §10.2), and any YouTube thumbnail/frame capture is a separate reviewed decision. Until then the corpus is the reviewed research datapack plus user-submitted URLs. *(No image ingestion path exists; the catalog is populated only from a reviewed dataset package.)*
  - [x] **B-S26.6** Enforce the ADR 0007 safeguards: authenticated surfaces only, blur-by-default projections, no person indexing/search/ranking, and the corpus never leaves the private repo or first-party storage. *(`form_note` and `alt_text` support blur-by-default; the image prompt forbids identifying anyone; no search or ranking endpoint exists.)*
  - [x] **B-S26.7** Test signed-URL expiry, annotation/prediction separation, classification schema validity, anonymous denial, and absence of image bytes in API responses and logs.
  - [x] **B-S26.6 amendment (24 Aug 2026)** Blur-by-default is superseded by ADR 0010: images are visible by default to an authenticated viewer, blurring is a persisted profile preference, and every image keeps a Show/Hide control. Authentication, signed URLs, private storage, safe alt text, and the no-person-indexing rule are unchanged.

- [ ] **B-S28 — Implement authenticated multipart image upload (completion guide step 8)**
  - [ ] **B-S28.1** Define the upload contract and update `spec.md` §13, OpenAPI, contract tests, and the frontend schemas together.
  - [ ] **B-S28.2** Accept one bounded JPEG/PNG/WebP; document exact byte and dimension limits.
  - [ ] **B-S28.3** Validate MIME from bytes; reject malformed, polyglot, and decompression-bomb files; never trust the filename.
  - [ ] **B-S28.4** Strip EXIF and other unnecessary personal metadata before storage.
  - [ ] **B-S28.5** Compute SHA-256 and enforce a documented duplicate policy.
  - [ ] **B-S28.6** Write bytes to the private first-party bucket; store owner, path, hash, MIME, size, timestamps, retention state, and classification references in PostgreSQL. Never base64 in the database.
  - [ ] **B-S28.7** Replace the Supabase JWT signing secret used as a Storage credential with a dedicated server-only provider credential, and replace custom HMAC URLs with official Storage API signed URLs or an authenticated backend stream.
  - [ ] **B-S28.8** Fetch stored bytes server-side and classify through the controlled Gemini boundary; keep upload, dataset annotation, model prediction, and human review as separate concepts.
  - [ ] **B-S28.9** Obtain explicit migration authorization before adding any schema the upload needs.
  - [ ] **B-S28.10** Define demo retention and deletion for user uploads.
  - [ ] **B-S28.11** Rate limit, and test anonymous denial, ownership, wrong MIME, oversized body, malformed image, metadata stripping, duplicate hash, missing object, signed-URL expiry, Gemini failure, logging redaction, and deletion.

## TRACK: devops

### Milestone 7 — Scheduling, CI, deployment, and demo readiness

- [x] **B-S21 — Assemble the idempotent ETL command and eight-hour workflow**
  - [x] **B-S21.1** Read DevOps/security/documentation rules and obtain explicit instruction before editing CI/CD configuration.
  - [x] **B-S21.2** Assemble discover → fetch → canonicalize → normalize → classify → aggregate → insights → finalize.
  - [x] **B-S21.3** Persist stage checkpoints and make reruns resumable/idempotent.
  - [x] **B-S21.4** Add scheduled execution at `17 */8 * * *` and constrained manual dispatch.
  - [x] **B-S21.5** Constrain dispatch to configured sources, query IDs, approved datapack manifest IDs, item caps, and dry-run.
  - [x] **B-S21.6** Prevent overlapping production ETL runs.
  - [x] **B-S21.7** Enable optional connectors only when approved/configured; otherwise report disabled/access-required.
  - [x] **B-S21.8** Upload only redacted run summaries with counts, warnings, and safe error codes.
  - [x] **B-S21.9** Provide an explicitly labelled fixture mode and test workflow/config validation.
  - [x] **B-S21.10** Include reviewed datapack import → canonicalize in manual/scheduled ETL with manifest selection constrained to approved configuration.
  - [x] **B-S21.11** Accept only approved stable registry keys/config versions for seed runs; never schedule directly from the Markdown registry.

- [ ] **B-S23 — Complete CI, AI evals, security gates, deployment, and smoke runbooks**
  - [x] **B-S23.1** Obtain explicit instruction before adding/changing CI/CD configuration.
  - [x] **B-S23.2** Add deterministic lint, format, type, unit, integration, contract, and fixture-E2E CI gates.
  - [x] **B-S23.3** Add disposable-Postgres migration/RLS and OpenAPI compatibility tests.
  - [x] **B-S23.4** Add dependency, secret, forbidden-file, and frontend-bundle scans.
  - [x] **B-S23.5** Add AI evals for schema, citations/numbers, benign-Muslim false positives, abstention, causality, prompt injection, and data-transfer/tool refusal.
  - [x] **B-S23.6** Ensure CI has no live provider calls, production secrets, or harmful raw content.
  - [x] **B-S23.7** Add Render health/readiness/deployment configuration and safe environment handoff documentation.
  - [x] **B-S23.8** Add deployed smoke tests proving health/readiness remain anonymous, all `/v1` product routes deny anonymous access, and an authenticated demo account completes a deterministic vertical slice.
  - [x] **B-S23.9** Document rollback, missing keys, manual ETL, fixture fallback, known limitations, and live/mock inventory.
  - [ ] **B-S23.10** Run all gates and freeze scope after acceptance blockers are resolved. *(Local verification passed except for 401 PostgreSQL-backed tests skipped without `AMANAH_TEST_DATABASE_URL`; CI now provisions PostgreSQL. The deployed smoke also requires the target URL and short-lived demo token.)*

## Cross-cutting gates

### Gate evidence recorded 24 August 2026

Run from the repository root on Windows 11 / PowerShell against this checkout.
A gate below stays unchecked where its evidence is still missing; nothing here is
checked because a test file exists.

| Command | Result |
|---|---|
| `uv run --project backend pytest backend/tests` | **532 passed, 401 skipped.** The skips are the PostgreSQL-backed database, migration, constraint, and RLS tests: `AMANAH_TEST_DATABASE_URL` was unset, and no local Postgres or running Docker daemon was available. `BE-GATE-TEST-02` therefore stays open. |
| `uv run --project backend ruff check backend/src backend/tests backend/migrations` | All checks passed. |
| `uv run --project backend ruff format --check backend/src backend/tests backend/migrations` | 239 files already formatted. |
| `uv run --project backend mypy backend/src backend/tests` | Success: no issues found in 230 source files. |
| `uv run --project backend --env-file backend/.env python -c "from amanah.main import create_app; create_app()"` | Starts; reports `disabled_connectors: [gemini, youtube, news]` because those keys are still placeholders. |
| OpenAPI enumeration from `create_app().openapi()` | 45 paths; `/healthz` and `/readyz` are the only unauthenticated ones. Every path the frontend live provider calls exists. |
| `npm --prefix apps/web run verify` | Format check, lint, type check, **345 tests passed**. |
| `npm --prefix apps/web run build` | Built clean; largest chunk 252 kB, under Vite's 500 kB warning. |
| Running service, `GET /readyz` | `{"status":"ready","checks":{"configuration":"ok","database":"ok"}}` — the configured Postgres is reachable. |
| Running service, anonymous `GET` on `/v1/dashboard`, `/v1/news`, `/v1/items`, `/v1/filters`, `/v1/me`, `/v1/insights`, `/v1/image-examples`, `/v1/me/contributions`, `/v1/me/posts` | **401 on every route.** |
| Running service, anonymous `POST` on `/v1/assistant/query`, `/v1/prepared-reports`, `/v1/research-reports`, `/v1/image-classifications`, `/v1/insights` | **401 on every route.** |
| Running service, `GET /v1/me` with a malformed bearer token | 401 with the safe envelope `AUTHENTICATION_REQUIRED` and a `request_id`; no stack trace, no provider text. |
| Response headers on `/healthz` | `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, `Cache-Control: no-store`. |

Still outstanding for the demo: a Postgres target for `BE-GATE-TEST-02`, real
provider credentials for `BE-GATE-TEST-07` and `BE-GATE-DOC-09`, and the deployed
smoke run for `BE-GATE-TEST-09` / `B-S23.10`.

### Security review

- [ ] **BE-GATE-SEC-01** Complete a threat model for authentication, Supabase access, user URL retrieval, Gemini transfer, provider adapters, reporting assistance, and exports.
- [ ] **BE-GATE-SEC-02** Verify anonymous denial for all product data plus least-privilege authorization for base user, owner, reviewer, and admin roles.
- [ ] **BE-GATE-SEC-03** Verify no secrets/tokens/credentials appear in code, fixtures, logs, artifacts, OpenAPI, frontend bundles, or committed environment files.
- [ ] **BE-GATE-SEC-04** Verify SSRF defenses across DNS resolution and every redirect with time/byte/type limits.
- [ ] **BE-GATE-SEC-05** Verify external/provider/model input validation and safe output encoding/projection.
- [ ] **BE-GATE-SEC-06** Verify harmful content, OCR, authors, prompts, signed URLs, and provider bodies are absent from logs/errors/artifacts.
- [ ] **BE-GATE-SEC-07** Verify Gemini data-class/transfer gates, prompt-injection resistance, and absence of arbitrary tools.
- [ ] **BE-GATE-SEC-08** Verify reporting assistance cannot submit externally, target arbitrary URLs, or facilitate mass reporting.
- [ ] **BE-GATE-SEC-09** Verify rate limits and idempotency for authentication, submissions, disputes, policy analysis, prepared reports, and report generation.
- [ ] **BE-GATE-SEC-10** Complete the `AGENTS.md` adversarial review and resolve or explicitly track every numbered finding.
- [ ] **BE-GATE-SEC-11** Verify datapack manifests, hashes, licenses, paths, schema mappings, and row errors cannot bypass approval or leak harmful content.

### Testing gate

- [ ] **BE-GATE-TEST-01** Backend unit tests pass.
- [ ] **BE-GATE-TEST-02** Real-database integration, migration, constraint, and RLS tests pass.
- [ ] **BE-GATE-TEST-03** API and source-adapter contract tests pass.
- [ ] **BE-GATE-TEST-04** Fixture vertical-slice E2E tests pass without live providers/secrets.
- [ ] **BE-GATE-TEST-05** Negative auth, ownership, validation, idempotency, retry, failure, quota, stale, and redaction tests pass.
- [ ] **BE-GATE-TEST-06** URL security tests cover private/reserved destinations, redirect chains, DNS rebinding, oversized bodies, timeouts, and unsupported content.
- [ ] **BE-GATE-TEST-07** AI evals cover benign Muslim content, counterspeech/quotation, ambiguity, schema validity, citations/numbers, causality, prompt injection, and abstention.
- [ ] **BE-GATE-TEST-08** Lint, format check, type check, dependency scan, and secret scan pass.
- [ ] **BE-GATE-TEST-09** Deployed health/readiness, anonymous product-denial, and authenticated vertical-slice smoke tests pass.
- [ ] **BE-GATE-TEST-10** No existing test was deleted, weakened, disabled, or skipped to obtain a pass.
- [ ] **BE-GATE-TEST-11** Datapack import contract/integration tests prove `N/A` source mapping and complete package/version/license/import/row provenance.
- [ ] **BE-GATE-TEST-12** Registry tests prove inactive candidates cannot run, unavailable seeds become coverage gaps, language/caps are enforced, and sampling strata cannot be silently combined.

### Documentation gate

- [ ] **BE-GATE-DOC-01** Backend README setup and commands are current and verified.
- [ ] **BE-GATE-DOC-02** OpenAPI matches implemented endpoints, filters, schemas, status codes, errors, and idempotency behavior.
- [ ] **BE-GATE-DOC-03** Architecture and trust-boundary diagrams reflect web, API, Supabase, Gemini, ETL, and providers.
- [ ] **BE-GATE-DOC-04** ADRs record the chosen stack, canonical adapter contract, Gemini boundary, and retention override behavior where required by `/rules`.
- [ ] **BE-GATE-DOC-05** Environment-variable documentation contains names and purpose only, never values.
- [ ] **BE-GATE-DOC-06** Runbooks cover manual ETL, stale/provider outage, quota exhaustion, Gemini failure, rollback, compromised secret, and fixture fallback.
- [ ] **BE-GATE-DOC-07** Dataset/model/prompt/taxonomy versions and AI limitations are documented.
- [ ] **BE-GATE-DOC-08** Resource and platform-policy catalogs record source URL, version/review date, and governance owner.
- [ ] **BE-GATE-DOC-09** Live, fixture, disabled, and approval-required integrations match the deployed state.
- [ ] **BE-GATE-DOC-10** Any divergence from `spec.md`, the plan, or `/rules` has explicit written approval and rationale.
- [ ] **BE-GATE-DOC-11** Every imported Kaggle/open datapack has a reviewed manifest and dataset card recording provenance, license, permitted use, hash, mapping version, and known limitations.
- [ ] **BE-GATE-DOC-12** Approved registry entries have stable runtime keys, review/approval metadata, configuration versions, sampling disclosures, and a documented mapping back to `PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`.
