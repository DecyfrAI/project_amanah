# Project Amanah — Backend, ML, and DevOps Todo Checklist

**Source of truth:** [`spec.md`](./spec.md)  
**Candidate source catalog:** [`PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`](./PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md) — review input only  
**Implementation plan:** [`backend-implementation-plan.md`](./backend-implementation-plan.md)  
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

- [ ] **B-S3 — Create the core database schema and RLS foundation**
  - [ ] **B-S3.1** Read the database plan/rules and confirm explicit authorization before changing migration files.
  - [ ] **B-S3.2** Add core source, run, content, prediction, metric, user, contribution, dispute, review, policy, resource, and report tables.
  - [ ] **B-S3.3** Use UUID keys, UTC timestamps, explicit enums, foreign keys, and documented check/unique constraints.
  - [ ] **B-S3.4** Add only query-driven indexes and verify expected access paths.
  - [ ] **B-S3.5** Make review/contribution decisions append-only and ready report snapshots immutable.
  - [ ] **B-S3.6** Add authenticated-safe projections that exclude encrypted/raw content and author identifiers.
  - [ ] **B-S3.7** Deny anonymous access to every product table/view/function/storage object and add authenticated base-role, owner, reviewer, and admin RLS boundaries.
  - [ ] **B-S3.8** Test empty-database migrations, constraints, negative RLS cases, and supported migration compatibility.
  - [ ] **B-S3.9** Add dataset package and import-run tables plus package/version/license/file-hash/schema-mapping/row provenance.
  - [ ] **B-S3.10** Map datapack items to the controlled `N/A` source row while preserving separate dataset provenance.
  - [ ] **B-S3.11** Add source-seed configuration storage constrained by stable registry key/config version with approval, language, cap, query purpose, and sampling stratum.

- [ ] **B-S5 — Implement authenticated dashboard and item read APIs**
  - [ ] **B-S5.1** Implement parameterized repositories for dashboard metrics, headlines, news, item lists, and item detail.
  - [ ] **B-S5.2** Support all validated authenticated filters and stable documented sorts.
  - [ ] **B-S5.3** Implement cursor pagination with stable secondary ordering.
  - [ ] **B-S5.4** Return numerator, denominator, scope, window, coverage, and data mode for every rate.
  - [ ] **B-S5.5** Preserve missing buckets as gaps and expose stale/partial warnings.
  - [ ] **B-S5.6** Exclude raw fields, author identifiers, and unauthorized evidence.
  - [ ] **B-S5.7** Test filters, cursors, unsupported inputs, empty data, redaction, representative query plans, and anonymous denial for every read route.
  - [ ] **B-S5.8** Add a distinct Dataset filter and return dataset provider/name/version separately from source/platform `N/A`.

- [ ] **B-S6 — Implement authenticated methodology, resources, and connection-status reads**
  - [ ] **B-S6.1** Implement authenticated methodology disclosures for sampling, taxonomy, models, coverage, and limitations.
  - [ ] **B-S6.2** Implement authenticated base-role reads for published resource entries only.
  - [ ] **B-S6.3** Return resource organization, country/scope, category, summary, URL, and last-reviewed date.
  - [ ] **B-S6.4** Implement safe connector state with purpose, status, last success/check, and safe warnings.
  - [ ] **B-S6.5** Ensure connector responses never include keys, connection strings, or raw provider failures.
  - [ ] **B-S6.6** Add caching and invalidation only where justified.
  - [ ] **B-S6.7** Test anonymous denial, unpublished-resource denial, and secret-free methodology/connector serialization.

### Milestone 3 — Collection and canonical processing

- [ ] **B-S7 — Implement collection-run and background-job state machines**
  - [ ] **B-S7.1** Implement valid transitions for queued, running, retry_wait, succeeded, failed, policy_blocked, and cancelled.
  - [ ] **B-S7.2** Persist idempotency/natural keys for runs and jobs.
  - [ ] **B-S7.3** Claim jobs transactionally with leases and recover expired claims safely.
  - [ ] **B-S7.4** Checkpoint stage output before enqueueing the next stage.
  - [ ] **B-S7.5** Store bounded retry metadata, next-run time, dead-letter state, and safe errors.
  - [ ] **B-S7.6** Add admin run create/read endpoints with source/window/item-cap validation.
  - [ ] **B-S7.7** Test duplicate delivery, concurrency, invalid transitions, lease loss, retry, and partial failure.

- [ ] **B-S8 — Implement the canonical adapter contract and fixture adapter**
  - [ ] **B-S8.1** Define discover, fetch, canonicalize, checkpoint, and health-check responsibilities.
  - [ ] **B-S8.2** Define one canonical `ContentItem` for news, social, and user-submitted sources.
  - [ ] **B-S8.3** Implement deterministic synthetic/redacted fixture discovery and processing.
  - [ ] **B-S8.4** Mark fixture records and runs explicitly through storage/API projections.
  - [ ] **B-S8.5** Persist adapter/config versions, cursors, and coverage counts.
  - [ ] **B-S8.6** Add a reusable adapter contract test suite.
  - [ ] **B-S8.7** Add an end-to-end fixture run that proves idempotent re-execution.
  - [ ] **B-S8.8** Extend canonical content for open datapacks with source/platform `N/A` and separate package/import/row provenance.
  - [ ] **B-S8.9** Define approved seed configuration with stable registry key, query family/purpose, sampling stratum, language, item cap, approval, and config version.
  - [ ] **B-S8.10** Keep `PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md` as human reference input; never parse it or auto-activate its entries at runtime.

- [ ] **B-S9 — Implement bounded news ingestion**
  - [ ] **B-S9.1** Select/configure GDELT and/or reviewed RSS without embedding credentials.
  - [ ] **B-S9.2** Store headline, publisher, canonical URL, permitted excerpt, publication/retrieval time, language, scope, and explicit location only.
  - [ ] **B-S9.3** Avoid full-article storage, paywall bypass, and unauthorized scraping.
  - [ ] **B-S9.4** Deduplicate by canonical URL and normalized provider/headline.
  - [ ] **B-S9.5** Add timeouts, result/byte limits, rate handling, checkpoints, and coverage warnings.
  - [ ] **B-S9.6** Test malformed, partial, duplicate, paginated, rate-limited, and outage responses at the HTTP boundary.

- [ ] **B-S9A — Implement reviewed open-datapack ingestion**
  - [ ] **B-S9A.1** Define a reviewed manifest for provider, dataset name/version, landing page, license, permitted uses, retrieval time, file hash, schema mapping, and approval.
  - [ ] **B-S9A.2** Import reviewed UTF-8 CSV and JSONL files without adding an ungoverned download crawler.
  - [ ] **B-S9A.3** Validate manifest, approval, license, SHA-256, encoding, required columns, schema mapping, and stable row identity before content writes.
  - [ ] **B-S9A.4** Map every row to source kind `open_datapack` and public source/platform `N/A`.
  - [ ] **B-S9A.5** Persist provider/name/version/license/file/import/row provenance separately.
  - [ ] **B-S9A.6** Store original dataset labels as dataset annotations only, never as Amanah predictions/reviews.
  - [ ] **B-S9A.7** Enforce `(dataset_package_id, dataset_row_id)` idempotency and cross-package collision safety.
  - [ ] **B-S9A.8** Stream/batch within configured limits and record imported/skipped/error counts without harmful raw text in logs.
  - [ ] **B-S9A.9** Test valid CSV/JSONL, duplicate/cross-package rows, malformed rows, wrong hash, bad encoding, unapproved license, retry, and `N/A` projection.

- [ ] **B-S10 — Implement bounded YouTube ingestion**
  - [ ] **B-S10.1** Enable the adapter only when an API key and approved configuration are present.
  - [ ] **B-S10.2** Implement official query and seed-video discovery modes.
  - [ ] **B-S10.3** Retrieve bounded video metadata, top-level comments, and replies through official APIs.
  - [ ] **B-S10.4** Persist source IDs, query purpose, window, timestamps, and adapter/config version.
  - [ ] **B-S10.5** Record disabled comments, deleted/omitted replies, quota deferral, and coverage gaps.
  - [ ] **B-S10.6** Checkpoint pagination and enforce query/video/comment caps.
  - [ ] **B-S10.7** Prohibit scraping or unsupported transcript retrieval.
  - [ ] **B-S10.8** Test pagination, quota, disabled comments, partial replies, deletion, retry, and missing key.
  - [ ] **B-S10.9** Project only approved registry seed/query entries into runtime configuration and persist their stable provenance.
  - [ ] **B-S10.10** Keep enriched, boundary/control, and ordinary-monitoring strata separate and enforce the English-only MVP language gate.
  - [ ] **B-S10.11** Test unknown/unapproved registry keys, unavailable seeds as coverage gaps, cap enforcement, and stratum provenance.

- [ ] **B-S11 — Implement safe user-URL retrieval**
  - [ ] **B-S11.1** Accept and normalize only public HTTP(S) URLs.
  - [ ] **B-S11.2** Reject credentials, unsafe ports, private/reserved/link-local targets, and prohibited schemes before network access.
  - [ ] **B-S11.3** Resolve DNS safely, revalidate every redirect, and prevent DNS-rebinding/private-destination access.
  - [ ] **B-S11.4** Enforce connect/read/total timeouts, redirect limits, byte limits, and content-type allowlists.
  - [ ] **B-S11.5** Extract metadata/permitted excerpts only and never invoke a shell or general browser.
  - [ ] **B-S11.6** Return explicit duplicate, unsupported, inaccessible, rejected, and failed states.
  - [ ] **B-S11.7** Test localhost/IP encodings, redirects, oversized bodies, malformed content, paywalls, duplicates, and timeout behavior.

- [ ] **B-S12 — Implement normalization and deduplication**
  - [ ] **B-S12.1** Preserve permitted original/encrypted text separately from normalized/model text.
  - [ ] **B-S12.2** Normalize Unicode and whitespace without destroying punctuation, emoji, quotes, identity terms, or stance context.
  - [ ] **B-S12.3** Assemble bounded source-aware title/parent/root/caption context.
  - [ ] **B-S12.4** Record language and explicit null/unavailable semantics.
  - [ ] **B-S12.5** Implement canonical source/URL keys and exact content hashes.
  - [ ] **B-S12.6** Version normalization and make content upserts retry-idempotent.
  - [ ] **B-S12.7** Test Unicode, counterspeech, quotation, missing context, duplicate source IDs, canonical URLs, and repeat execution.
  - [ ] **B-S12.8** Deduplicate datapack rows by dataset package/row identity without collapsing the same row ID across different packages.

### Milestone 5 — Authenticated contributions and human review

- [ ] **B-S16 — Implement URL submissions and contribution history**
  - [ ] **B-S16.1** Add authenticated one-public-URL submission with server-side validation.
  - [ ] **B-S16.2** Enforce idempotency and link canonical duplicates rather than reprocessing.
  - [ ] **B-S16.3** Persist Processing before enqueueing safe retrieval/canonical processing.
  - [ ] **B-S16.4** Append user-safe contribution events for every status transition.
  - [ ] **B-S16.5** Support processing, analyzed, duplicate, unsupported, inaccessible, rejected, and failed.
  - [ ] **B-S16.6** Return cursor-paginated contributions owned by the authenticated user only.
  - [ ] **B-S16.7** Rate-limit submissions and test auth, ownership, idempotency, transition, and enqueue behavior.

- [ ] **B-S17 — Implement disputes and reviewer decisions**
  - [ ] **B-S17.1** Enforce one open dispute per user/item.
  - [ ] **B-S17.2** Return/link the existing dispute on an idempotent duplicate request.
  - [ ] **B-S17.3** Create prioritized review tasks without changing the original prediction.
  - [ ] **B-S17.4** Implement reviewer claim, append-only decision, and history endpoints with leases and roles.
  - [ ] **B-S17.5** Update effective-label projections from review events while preserving history.
  - [ ] **B-S17.6** Append a user-safe resolution to the user’s contribution timeline.
  - [ ] **B-S17.7** Quarantine approved corrections as training candidates; never auto-train.
  - [ ] **B-S17.8** Test concurrent claims, invalid decisions, ownership, immutability, duplicate disputes, and final outcomes.

- [ ] **B-S18 — Implement platform-policy assistance and prepared reports**
  - [ ] **B-S18.1** Add at least one reviewer-approved official platform-policy fixture/catalog entry with version and review date.
  - [ ] **B-S18.2** Return constrained candidate policy matches with uncertainty and official links.
  - [ ] **B-S18.3** Require explicit user-selected/confirmed policy ID and version before saving.
  - [ ] **B-S18.4** Persist evidence summary, suggested wording, item, platform, policy version, user, and creation time.
  - [ ] **B-S18.5** Implement prepared/submitted/outcome state transitions without claiming platform receipt.
  - [ ] **B-S18.6** Prohibit platform reporting API calls, arbitrary destinations, and automatic submission.
  - [ ] **B-S18.7** Add per-user/item abuse controls and anti-brigading limits.
  - [ ] **B-S18.8** Test stale policies, low confidence, confirmation, ownership, outcomes, and absence of external side effects.

### Milestone 6 — Research reports and curated resources

- [ ] **B-S19 — Implement curated resource administration and governance**
  - [ ] **B-S19.1** Add reviewer/admin create, update, publish, archive, and list operations.
  - [ ] **B-S19.2** Validate HTTPS URL, organization, category, country/scope, summary, reviewer, and last-reviewed date.
  - [ ] **B-S19.3** Implement draft, published, and archived lifecycle.
  - [ ] **B-S19.4** Keep audit history and publish only reviewed entries.
  - [ ] **B-S19.5** Keep unreviewed candidate content in draft; do not publish raw AI-generated descriptions.
  - [ ] **B-S19.6** Test roles, validation, publication, archive, audit, anonymous denial, and authenticated base-role projection.

- [ ] **B-S20 — Implement research-report snapshots and aggregate export**
  - [ ] **B-S20.1** Validate authorized report filters and resolve the exact data/methodology versions.
  - [ ] **B-S20.2** Freeze coverage, denominators, selected metrics/findings, and citation IDs.
  - [ ] **B-S20.3** Apply redaction and exclude raw harmful content, authors, and item-level bulk data by default.
  - [ ] **B-S20.4** Make ready snapshots immutable; regenerate under a new ID.
  - [ ] **B-S20.5** Generate aggregate CSV from the stored snapshot if included in scope.
  - [ ] **B-S20.6** Enforce owner/reviewer authorization and audit generation/download.
  - [ ] **B-S20.7** Test filter/citation fidelity, immutability, redaction, CSV schema, and cross-user denial.

### Milestone 7 — Production resilience and observability

- [ ] **B-S22 — Add production resilience and observability**
  - [ ] **B-S22.1** Add structured redacted logs with request/run/job correlation.
  - [ ] **B-S22.2** Add documented metrics for API, connector, Gemini, job, contribution, review, and report behavior.
  - [ ] **B-S22.3** Apply explicit dependency timeouts and bounded transient retries with jitter.
  - [ ] **B-S22.4** Add per-IP/user rate limits and correct `Retry-After` behavior.
  - [ ] **B-S22.5** Preserve last-successful data with stale/partial coverage; never silently swap fixtures.
  - [ ] **B-S22.6** Isolate connector/item failures and implement accurate health/readiness semantics.
  - [ ] **B-S22.7** Test provider outages, quota exhaustion, Gemini deferral, DB failure, lease loss, partial extraction, and auth expiry.

## TRACK: ml

### Milestone 4 — AI classification and research insights

- [ ] **B-S13 — Implement the controlled Gemini client**
  - [ ] **B-S13.1** Read `rules/ml.md`, `rules/agentic.md`, security/testing rules, and the AI sections of `spec.md`.
  - [ ] **B-S13.2** Configure Gemini model/key through validated server settings only.
  - [ ] **B-S13.3** Add strict structured input/output schemas and a prompt/version registry.
  - [ ] **B-S13.4** Add deterministic cache keys using content/data/model/prompt/taxonomy versions.
  - [ ] **B-S13.5** Add timeouts, bounded retries, context/output caps, and per-run/daily token budgets.
  - [ ] **B-S13.6** Enforce data-class/transfer authorization before constructing a request.
  - [ ] **B-S13.7** Treat content as prompt-injection data and expose no arbitrary SQL/network/tools.
  - [ ] **B-S13.8** Return typed success, deferred, policy-blocked, invalid-output, and provider-failure results.
  - [ ] **B-S13.9** Test cache, schema failure, timeouts, budgets, prompt injection, and prohibited transfer.

- [ ] **B-S14 — Implement staged classification and confidence**
  - [ ] **B-S14.1** Separate relevance, stance, multi-label type, severity, narrative, score, rationale, and review need.
  - [ ] **B-S14.2** Represent counterspeech/quotation and uncertainty explicitly.
  - [ ] **B-S14.3** Map numeric scores to versioned configurable Low/Medium/High tiers.
  - [ ] **B-S14.4** Mark default thresholds provisional until calibrated on a reviewed holdout.
  - [ ] **B-S14.5** Persist model, prompt, taxonomy, normalization, and inference versions without overwriting older predictions.
  - [ ] **B-S14.6** Route low-confidence, uncertain, severe, invalid, and disagreement cases to review.
  - [ ] **B-S14.7** Build a frozen licensed/synthetic/redacted evaluation set with benign Muslim, news, criticism, counterspeech, coded, ambiguous, and injection cases.
  - [ ] **B-S14.8** Report confusion/calibration/false-positive slices without inventing an accuracy claim.

- [ ] **B-S15 — Implement deterministic metrics and cached insights**
  - [ ] **B-S15.1** Compute observed, relevant, likely-hate, reviewed, and confirmed counts outside Gemini.
  - [ ] **B-S15.2** Compute the monitored-sample likely anti-Muslim rhetoric rate with numerator and denominator.
  - [ ] **B-S15.3** Store coverage, gaps, filter version, and bucket provenance.
  - [ ] **B-S15.4** Build bounded fact bundles with immutable IDs and exact filters.
  - [ ] **B-S15.5** Require every Gemini quantitative claim/citation to validate against the fact bundle.
  - [ ] **B-S15.6** Separate observed facts, interpretation, possible association, and unknowns; reject causal language.
  - [ ] **B-S15.7** Cache by filter/data/model/prompt version and preserve deterministic results when AI fails.
  - [ ] **B-S15.8** Test aggregation, missing coverage, citation/numeric fidelity, causal refusal, insufficient data, and cache behavior.
  - [ ] **B-S15.9** Group by sampling stratum and prevent enriched seed, boundary/control, and ordinary-monitoring results from silently becoming a prevalence metric.

## TRACK: devops

### Milestone 7 — Scheduling, CI, deployment, and demo readiness

- [ ] **B-S21 — Assemble the idempotent ETL command and eight-hour workflow**
  - [ ] **B-S21.1** Read DevOps/security/documentation rules and obtain explicit instruction before editing CI/CD configuration.
  - [ ] **B-S21.2** Assemble discover → fetch → canonicalize → normalize → classify → aggregate → insights → finalize.
  - [ ] **B-S21.3** Persist stage checkpoints and make reruns resumable/idempotent.
  - [ ] **B-S21.4** Add scheduled execution at `17 */8 * * *` and constrained manual dispatch.
  - [ ] **B-S21.5** Constrain dispatch to configured sources, query IDs, approved datapack manifest IDs, item caps, and dry-run.
  - [ ] **B-S21.6** Prevent overlapping production ETL runs.
  - [ ] **B-S21.7** Enable optional connectors only when approved/configured; otherwise report disabled/access-required.
  - [ ] **B-S21.8** Upload only redacted run summaries with counts, warnings, and safe error codes.
  - [ ] **B-S21.9** Provide an explicitly labelled fixture mode and test workflow/config validation.
  - [ ] **B-S21.10** Include reviewed datapack import → canonicalize in manual/scheduled ETL with manifest selection constrained to approved configuration.
  - [ ] **B-S21.11** Accept only approved stable registry keys/config versions for seed runs; never schedule directly from the Markdown registry.

- [ ] **B-S23 — Complete CI, AI evals, security gates, deployment, and smoke runbooks**
  - [ ] **B-S23.1** Obtain explicit instruction before adding/changing CI/CD configuration.
  - [ ] **B-S23.2** Add deterministic lint, format, type, unit, integration, contract, and fixture-E2E CI gates.
  - [ ] **B-S23.3** Add disposable-Postgres migration/RLS and OpenAPI compatibility tests.
  - [ ] **B-S23.4** Add dependency, secret, forbidden-file, and frontend-bundle scans.
  - [ ] **B-S23.5** Add AI evals for schema, citations/numbers, benign-Muslim false positives, abstention, causality, prompt injection, and data-transfer/tool refusal.
  - [ ] **B-S23.6** Ensure CI has no live provider calls, production secrets, or harmful raw content.
  - [ ] **B-S23.7** Add Render health/readiness/deployment configuration and safe environment handoff documentation.
  - [ ] **B-S23.8** Add deployed smoke tests proving health/readiness remain anonymous, all `/v1` product routes deny anonymous access, and an authenticated demo account completes a deterministic vertical slice.
  - [ ] **B-S23.9** Document rollback, missing keys, manual ETL, fixture fallback, known limitations, and live/mock inventory.
  - [ ] **B-S23.10** Run all gates and freeze scope after acceptance blockers are resolved.

## Cross-cutting gates

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
