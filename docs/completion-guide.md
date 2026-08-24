# Hackathon production demo completion checklist

**Document type:** How-to and completion reference  
**Last reviewed:** 24 August 2026  
**Target:** Publicly reachable hackathon production demo  
**Status:** Active — not yet accepted

## Progress, 24 August 2026

Work packages **1, 2, 6, 7, 9** and partner adjustments **PA-01 to PA-04** and
**PA-06** are implemented in the working tree. Gate evidence is recorded in
[`backend-todo.md`](./backend-todo.md) under *Gate evidence recorded 24 August
2026*.

What is implemented:

- Supabase authentication, session restoration, bearer tokens on every live
  request, `401` clearing the session, `403` kept distinct.
- A `demo` data mode that routes product data to the live API with no
  catch-and-fallback; remaining mocks are labelled in place.
- The frontend live provider reconciled against the shipped backend contracts
  (G1–G5, G7, G8 read paths), with wire schemas mirroring the Pydantic models.
- Assisted platform reporting through the policy catalogue, and research-report
  snapshot creation, CSV download, and print/PDF.
- PA-01 media preference (ADR 0010), PA-02 removal, PA-03 request-driven
  readiness, PA-04 return navigation, PA-06 root README.

What still blocks a **go**, and needs the operator rather than more code:

1. **Real credentials.** `GEMINI_API_KEY`, `GEMINI_MODEL`, Supabase Storage, and
   `VITE_SUPABASE_*` are still placeholders, so those connectors report
   themselves disabled.
2. **A Postgres target for the database gate.** 401 backend tests skip without
   `AMANAH_TEST_DATABASE_URL`.
3. **One reviewed RSS feed ingested,** and one reviewed datapack imported
   (work packages 3 and 5).
4. **Authenticated multipart image upload** (work package 8) — tracked as
   backend `B-S28`; the live path refuses visibly rather than pretending.
5. **PA-05 attachments** — needs an ADR 0004 supersede and migration
   authorization before implementation.
6. **Deployment and the deployed smoke run** (work package 12).

This document collects the work that remains for the hackathon demo. It does
not replace the product specification, implementation plans, TODOs, ADRs, or
runbooks. If this checklist conflicts with a governing document, the governing
document wins and this file must be corrected.

## Governing documents

- Product behavior and API scope: [`spec.md`](./spec.md)
- Backend implementation sequence: [`backend-implementation-plan.md`](./backend-implementation-plan.md)
- Backend completion record: [`backend-todo.md`](./backend-todo.md)
- Frontend implementation sequence: [`frontend-implementation-plan.md`](./frontend-implementation-plan.md)
- Frontend scope checklist: [`frontend-todo.md`](./frontend-todo.md)
- Current frontend work list: [`../apps/web/todo.md`](../apps/web/todo.md)
- Frontend/backend contract gaps: [`frontend-backend-reconciliation.md`](./frontend-backend-reconciliation.md)
- News source review and allowlist: [`news-rss-sources.md`](./news-rss-sources.md)
- Gemini trust boundary: [`adr/0009-gemini-boundary.md`](./adr/0009-gemini-boundary.md)
- Research image decision: [`adr/0007-research-image-corpus.md`](./adr/0007-research-image-corpus.md)
- Research image datapack notes: [`synthetic-image-datapack.md`](./synthetic-image-datapack.md)
- Deployment procedure: [`runbooks/deployment.md`](./runbooks/deployment.md)
- Operations procedure: [`runbooks/operations.md`](./runbooks/operations.md)
- Backend threat model: [`architecture/backend-threat-model.md`](./architecture/backend-threat-model.md)
- Binding repository instructions: [`../AGENTS.md`](../AGENTS.md) and [`../rules/`](../rules/)

## Accepted demo scope

The following paths must be real, authenticated, and backed by the deployed
API and PostgreSQL database:

- [ ] Supabase sign-in, session restoration, logout, and bearer-token handling.
- [ ] News ingestion from at least one reviewed RSS source and live `GET /v1/news` display.
- [ ] Gemini text classification and the grounded assistant using stored facts.
- [ ] One reviewed open datapack imported through the manifest-validated ETL path.
- [ ] Assisted platform-report preparation and persisted outcome tracking.
- [ ] Research-report snapshot creation and aggregate CSV; browser Print/Save as PDF may provide the PDF artifact.
- [ ] Authenticated image upload to private object storage and server-side Gemini classification.
- [ ] Health, readiness, safe errors, rate limits, and deployed smoke checks.

The remaining product surfaces may use synthetic fixtures, but each fixture
surface must be visibly labelled `Demo`, `Fixture`, or `Mock`. A failed live
request must never silently return a fixture result. This preserves the data-mode
requirements in [`spec.md`](./spec.md), backend gate `BE-GATE-DOC-09`, frontend
step `F-S20.5`, and reconciliation guidance `G1`–`G11`.

The following remain prohibited even in the demo:

- Automatic platform-report submission.
- Arbitrary reporting destinations or mass-reporting assistance.
- Browser calls to Gemini or another secret-backed provider.
- Person-level search, ranking, identity resolution, or repeat-offender views.
- Presenting an enriched or fixture sample as platform-wide prevalence.
- Importing a datapack without approval, license review, hash verification, and provenance.
- Publishing the internal research image corpus in a public bucket or public repository.

## Partner adjustment register

The following adjustments were received after the initial demo scope was
written. Their status reflects the repository on 23 August 2026. A requested
behavior is not marked implemented merely because a similar-looking fixture
control exists.

### PA-01 — Make images visible by default and let the user enable blur

**Status:** Requested; partially scaffolded; governing-document change required.

Current behavior:

- [`SettingsPage.tsx`](../apps/web/src/features/settings/SettingsPage.tsx) has a
  “Blur media until I choose to view it” checkbox.
- It starts enabled, affects only the Settings preview, is not persisted, and
  does not reach Explorer, Review, Insights, Reports, or uploaded-image views.
- Individual image cards have local Reveal/Hide controls in some fixture views.

Adjustment:

- [ ] Change the default preference to **show images unblurred**.
- [ ] Let the user enable “Blur media by default” in Settings.
- [ ] Persist the preference through the authenticated profile preference
  boundary rather than page-local state.
- [ ] Apply the same preference to Explorer, Review, Insights, Reports, the
  image catalogue, and uploaded-image results.
- [ ] Keep an accessible per-image Show/Hide action so a user can override the
  global preference for one item.
- [ ] Apply a preference change immediately to already-rendered images without
  requiring a reload.
- [ ] Do not change text redaction, author removal, authentication, or signed-URL
  controls when changing the image-display preference.
- [ ] Test the default-off state, persisted opt-in blur, per-image override,
  keyboard operation, refresh restoration, and every affected route.

This reverses the current blur-by-default rule in [`spec.md`](./spec.md),
[`adr/0007-research-image-corpus.md`](./adr/0007-research-image-corpus.md), the
frontend plan's content-safety requirements, and the repository instructions.
Before implementation, record explicit product-owner approval in `spec.md` and
add a new ADR that supersedes or amends ADR 0007; do not edit the accepted ADR's
original decision text in place. The change must retain authenticated access,
safe alt text, deliberate controls, private storage, and no public harmful-media
gallery.

Acceptance:

- A new authenticated user sees images unblurred on every approved image surface.
- Enabling blur in Settings immediately blurs images in Explorer and Review and
  remains enabled after refresh and a new session.
- Disabling blur restores images without changing authorization or fetching an
  unsigned/public object.

### PA-02 — Remove unrelated images from the Insights list

**Status:** Existing behavior verified; removal or redesign required.

This is not an accidental CSS artifact. [`InsightsListPage.tsx`](../apps/web/src/features/insights/InsightsListPage.tsx)
always renders `ImageEvidenceList`. That component calls
[`useImagePosts.ts`](../apps/web/src/features/insights/useImagePosts.ts), which
requests an unfiltered Explorer page and selects every item with an image. The
images are not tied to a particular insight, fact bundle, discussion post, or
active insight window.

Adjustment:

- [ ] Remove the standalone, unscoped Image Evidence section from the Insights list.
- [ ] Remove its dedicated hook/components/tests if they have no remaining consumer.
- [ ] Keep research image discovery in the authenticated Explorer/Review/Reports
  surfaces selected for the demo.
- [ ] If an image is attached to a particular insight discussion under PA-05,
  show it only inside that discussion post with its provenance and access controls.
- [ ] Update Insights copy and tests so the page describes stored insights and
  their discussions, not an unrelated image feed.

Acceptance:

- Opening `/app/insights` does not issue an unrelated `/v1/items` image query.
- The page contains only insight summaries; attached media appears only inside
  the insight/thread it belongs to.

### PA-03 — Let real API readiness control the loading screen

**Status:** Not implemented; a fixed delay exists.

[`AppLoadingScreen.tsx`](../apps/web/src/components/ui/AppLoadingScreen.tsx)
defines a nine-second `ENTRY_HOLD_MS`. Fixture Login and Sign-up wait on that
timer before navigation, whether the application is ready earlier or later.

Adjustment:

- [ ] Remove the fixed post-login hold and the timer-driven navigation behavior.
- [ ] Navigate after Supabase authentication/session restoration succeeds.
- [ ] Keep the protected workspace loading state visible while the backend
  readiness/initial required query is genuinely pending.
- [ ] Use the real request lifecycle from the query/auth layer; do not estimate
  the API's boot time with another fixed delay.
- [ ] After a short threshold, change the copy to an honest cold-start message
  such as “The demo API is waking up.”
- [ ] Apply a bounded timeout and retry action so a failed API cannot leave the
  user on an infinite loading screen.
- [ ] Preserve accessible `aria-busy`/status announcements and reduced-motion behavior.
- [ ] Test immediate success, slow cold start, retryable failure, timeout,
  cancellation/unmount, and session expiry.

Acceptance:

- A warm API opens as soon as authentication and initial data are ready.
- A cold API keeps a truthful loading state for the actual request duration.
- A failed API ends in an actionable error/retry state, never a permanent loader.

### PA-04 — Make the Overview-to-Insights journey obvious

**Status:** Core navigation exists; explicit return/list action is missing.

[`useCreateInsight.ts`](../apps/web/src/features/insights/useCreateInsight.ts)
already invalidates the insight list and navigates directly to the newly created
insight detail page. The requested insight therefore is posted and opened, but
the detail page does not provide a prominent way to return to the complete
Insights list.

Adjustment:

- [ ] Keep the existing create-and-open behavior.
- [ ] Show a clear success state explaining that the snapshot was added to Insights.
- [ ] Add a `View all insights` link/button on the created insight detail page.
- [ ] Add the same return action to every insight detail page, including
  machine-generated insights.
- [ ] Preserve browser Back behavior and do not create duplicate insight records
  when the user clicks twice while the mutation is pending.
- [ ] Test figure/day/breakdown creation, list invalidation, direct navigation,
  return navigation, failure, and duplicate-click protection.

Acceptance:

- Clicking Start insight on Overview opens the stored insight.
- One obvious action returns to `/app/insights`, where the new item is visible.

### PA-05 — Add replies with image/file attachments to insight discussions

**Status:** Text notes partly implemented; nested replies and uploaded attachments are not.

Current behavior:

- Text notes can be added to both viewer snapshots and machine-generated insight
  detail pages through the shared `DiscussionPanel`.
- The discussion is flat; there is no `parent_post_id` or nested reply contract.
- The only attachment is an existing first-party Amanah dashboard capture named
  by `capture_id`.
- [`adr/0004-insight-discussion.md`](./adr/0004-insight-discussion.md) explicitly
  rejected arbitrary screenshot/file attachments and permits only first-party
  captures, so this adjustment changes an accepted architecture decision.

Adjustment:

- [ ] Decide whether “reply” means a flat note on an insight or a nested reply to
  a specific post. If nested replies are required, add `parent_post_id` and a
  bounded thread-depth rule to the spec, API, database, UI, and tests.
- [ ] Permit the chosen reply behavior on viewer-created and machine-generated insights.
- [ ] Define the exact allowed attachment types, maximum files, maximum bytes,
  retention, deletion, download, preview, and malware-scanning policy before implementation.
- [ ] Store uploaded files privately; store only ownership, metadata, hashes,
  storage paths, and relationships in PostgreSQL.
- [ ] Reuse the corrected authenticated upload/Storage boundary from the image
  upload work rather than adding a browser-to-provider path.
- [ ] Do not inline active HTML/SVG or execute document content; unsupported
  files must be refused, not renamed.
- [ ] Keep harmful images subject to the user's PA-01 display preference and an
  accessible per-attachment Show/Hide control.
- [ ] Enforce invitation, insight visibility, uploader ownership, post ownership,
  rate limits, and cross-user denial through the backend and RLS.
- [ ] Remove attachments from a retracted post without silently deleting the
  append-only discussion event.
- [ ] Add upload progress, retry, validation, unavailable, and safe-download UI.
- [ ] Test machine-generated insight replies, snapshot replies, nested-depth
  limits if applicable, unauthorized access, wrong type, oversized input,
  malformed content, duplicate hash, retraction, signed-URL expiry, and logging redaction.

Before implementation, update [`spec.md`](./spec.md) and add a superseding ADR
for ADR 0004. If new database columns/tables or Storage policies are needed,
obtain explicit migration authorization before editing protected migration files.

Acceptance:

- An invited demo user can add a permitted attachment to a discussion on both a
  viewer snapshot and a machine-generated insight.
- The attachment remains private and visible only to authorized participants.
- Retraction removes attachment access while preserving the retracted-event history.

### PA-06 — Add reviewer-focused project and deployment documentation

**Status:** Partially implemented; root README missing.

[`../apps/web/README.md`](../apps/web/README.md) describes the frontend and
[`../backend/README.md`](../backend/README.md) describes the service/API. A
backend-oriented deployment runbook exists at
[`runbooks/deployment.md`](./runbooks/deployment.md), but the repository root has
no `README.md`, which also violates [`rules/documentation.md`](../rules/documentation.md).

Adjustment:

- [ ] Create a concise reviewer-focused root `README.md`.
- [ ] Explain the story/problem, intended users, solution, research purpose,
  hackathon scope, key features, AI/human-review boundary, and limitations.
- [ ] Document the stack: React/Vite/TypeScript, FastAPI/Pydantic/SQLAlchemy,
  PostgreSQL/Supabase Auth and Storage, Gemini, Render, Netlify, and GitHub Actions.
- [ ] Add a small architecture/data-flow diagram or link the authoritative
  diagrams under [`architecture/`](./architecture/).
- [ ] Identify which demo features are live, fixture, mock, disabled, or approval-required.
- [ ] Explain News, datapack provenance, deterministic metrics, Gemini grounding,
  reporting safeguards, image handling, authentication, and role boundaries.
- [ ] Include prerequisites, quick start, test commands, demo walkthrough,
  screenshots or recording links when available, and links to deeper docs.
- [ ] Keep the root README concise and move operational detail to dedicated docs,
  consistent with [`rules/documentation.md`](../rules/documentation.md).
- [ ] Expand [`runbooks/deployment.md`](./runbooks/deployment.md) into a verified
  full-stack procedure covering Supabase, database connections/migrations/Auth/
  private Storage, Gemini, Render, Netlify, GitHub environments/ETL, RSS News,
  the selected datapack, smoke tests, monitoring, rollback, and secret rotation.
- [ ] Include Windows-specific commands where they differ, because the current
  workspace and primary novice walkthrough use PowerShell.
- [ ] Verify every setup/deployment command, relative link, environment-variable
  name, and health/smoke check before marking documentation gates complete.

Acceptance:

- A hackathon reviewer can understand the story, solution, trust boundaries,
  live/mock inventory, and demo journey from the root README.
- A novice developer can deploy a fresh staging environment by following the
  deployment runbook without relying on undocumented chat instructions.

## Current implementation status

| Capability | Implemented now | Remaining for the demo | Governing references |
|---|---|---|---|
| News | Backend RSS ingestion, reviewed allowlist behavior, `GET /v1/news`, publisher-metadata projection, pagination, and tests are implemented. The frontend already calls `/v1/news`. | Add real auth headers, verify nullable `published_at`/`scope`, configure and run one reviewed feed, test pagination/failure states, and prove the deployed UI uses live news. | Backend `B-S9`; frontend `F-S5`, `F-S21.1`, `F-S21.5`; reconciliation `G1`, `G5`; [`news-rss-sources.md`](./news-rss-sources.md). |
| Gemini | Controlled client, budgets, cache, schemas, ETL classification, grounded assistant, image classifier, and frozen evals exist. | Configure a model/key, run a permitted synthetic live call, pass evals, connect frontend auth, and verify deployed degradation and cost limits. | Backend `B-S13`–`B-S15`, `B-S25`, `B-S26`; [`adr/0009-gemini-boundary.md`](./adr/0009-gemini-boundary.md). |
| Open datapack | Manifest validation, CSV/JSONL import, hash/license/approval checks, provenance, idempotency, ETL selection, and DB tests exist. | Select one dataset, create its reviewed manifest and dataset card, add it to runtime configuration, import it, classify it, and show provenance. `config/datapacks.example.yml` currently has no packages. | Backend `B-S9A`, `B-S12.8`, `B-S21.10`; frontend `F-S2.7`, `F-S5.8`, `F-S6.8`, `F-S7.8`, `F-S8.8`; gates `BE-GATE-SEC-11`, `BE-GATE-DOC-11`. |
| Assisted reporting | Backend policy analysis, prepared-report persistence, state changes, ownership, and anti-brigading controls exist. | Replace the live frontend `501` stub with the policy-selection/save/outcome flow and Contributions integration. | Backend `B-S18`; frontend `F-S11`, `F-S14`, `F-S21.7`; reconciliation `G9`. |
| Research reports | Backend immutable snapshots and aggregate CSV exist. | Connect creation/read/download, replace mock snapshots, add Print/Save as PDF, and test authorization/redaction. | Backend `B-S20`; frontend `F-S16`, `F-S20.4`. |
| Image catalogue/classification | Backend catalogue and classification of an existing catalogued image exist; frontend fixture picker/preview exists. | Implement multipart upload, correct private Storage credentials and official signed URLs, persist upload metadata/ownership, send stored bytes to Gemini, connect the live frontend, and test retention/deletion. | Backend `B-S26`; reconciliation `G8`; [`adr/0007-research-image-corpus.md`](./adr/0007-research-image-corpus.md); [`synthetic-image-datapack.md`](./synthetic-image-datapack.md). |
| Authentication/live API | Backend bearer-token boundary exists. | Replace fixture `sessionStorage`, restore Supabase sessions, attach access tokens to every live request, and handle `401`/`403`. | Frontend `F-S9`, `F-S21.1`; reconciliation `G1`; [`../apps/web/todo.md`](../apps/web/todo.md). |
| Deployment acceptance | Render, Netlify, CI, ETL workflow, scans, smoke command, and runbooks exist. | Run PostgreSQL-backed gates in CI, deploy staging/production, execute deployed smoke, complete cross-cutting reviews, and freeze scope. | Backend `B-S23`, especially `B-S23.10`; backend security/testing/documentation gates; [`runbooks/deployment.md`](./runbooks/deployment.md). |

## Required implementation order

Complete the following work packages in order. A package is complete only when
its acceptance checks and referenced TODO items are updated with evidence.

### 1. Reconcile the completion records

- [ ] Add this demo scope to the active work plan without marking implementation complete.
- [ ] Add an explicit backend task for authenticated multipart image upload and private object-storage writes.
- [ ] Add an explicit frontend task for live image upload and classification.
- [ ] Amend the `B-S26` record: catalogued-image classification is implemented, but user upload is not.
- [ ] Add a task to replace the custom Storage credential/signing implementation with the official provider API.
- [ ] Add the hybrid live/mock provider and visible mock-inventory tasks to [`../apps/web/todo.md`](../apps/web/todo.md).
- [ ] Mark the stale “Add `netlify.toml`” task complete only after its current configuration is reviewed; [`../netlify.toml`](../netlify.toml) already exists.
- [ ] Keep backend `B-S23` and `B-S23.10` open until the real database and deployed smoke gates pass.
- [ ] Record any required database-schema change before editing migrations; migration files remain protected without explicit instruction.

Acceptance:

- The backend and frontend TODOs accurately distinguish implemented backend
  foundations from unconnected frontend or deployment work.
- No checked item claims that multipart image upload already exists.

### 2. Implement real authentication and the hybrid demo boundary

References: frontend `F-S9`, `F-S21.1`; reconciliation `G1`; backend `B-S4`;
[`spec.md`](./spec.md) authentication and authorization sections.

- [ ] Replace the fixture session in `apps/web/src/features/auth/session.ts` with the Supabase browser client.
- [ ] Restore the Supabase session before protected routes render.
- [ ] Complete login, logout, callback, recovery, expiry, and safe internal-return behavior required by `F-S9`.
- [ ] Attach the Supabase access token as `Authorization: Bearer ...` to every live request.
- [ ] Treat `401` as an expired/missing session and `403` as an authorization denial.
- [ ] Keep service-role, secret, database, Gemini, and Storage credentials out of browser variables and bundles.
- [ ] Add a clearly named demo provider that routes News, Gemini, datapack-backed reads, reports, and images to the live provider.
- [ ] Route intentionally mocked methods to the fixture provider without catch-and-fallback behavior.
- [ ] Preserve the actual `data_mode` on every response and add a persistent label on fixture/mock screens.
- [ ] Test that a live method failure remains a visible failure and never becomes fixture data.

Acceptance:

- An anonymous visitor cannot enter any protected route or call any `/v1` product endpoint.
- A signed-in demo user can refresh the page without losing a valid session.
- Browser network inspection shows bearer tokens on live calls and no server secret in browser code.
- The live/mock inventory is visible to judges and matches the deployed behavior.

### 3. Make News function end to end

References: backend `B-S9`; frontend `F-S5`, `F-S21.5`; reconciliation `G5`;
[`news-rss-sources.md`](./news-rss-sources.md); [`config/sources.example.yml`](../config/sources.example.yml);
[`config/source-seeds.example.yml`](../config/source-seeds.example.yml).

- [ ] Select at least one enabled RSS source already approved in the reviewed configuration.
- [ ] Do not invent or add a feed outside [`news-rss-sources.md`](./news-rss-sources.md) during demo freeze.
- [ ] Synchronize reviewed source, seed, and platform-policy configuration into the demo database.
- [ ] Run the selected RSS source in dry-run mode.
- [ ] Run one bounded real ingestion with a small item cap.
- [ ] Verify canonical URL/provider/headline deduplication by repeating the run.
- [ ] Verify topical relevance filtering keeps reviewed religion, hate-crime, mosque, court, election, or public-affairs coverage and removes rejected sport/celebrity material.
- [ ] Verify ingested news remains publisher context and receives no hate label, score, severity, or review state.
- [ ] Confirm `GET /v1/news` returns `window`, `applied`, `coverage`, `data_mode`, `next_cursor`, and publisher-metadata items.
- [ ] Update frontend validation for nullable `published_at` and `scope`, as recorded in reconciliation `G5`.
- [ ] Confirm the live provider sends the authenticated request to `/v1/news`.
- [ ] Render publisher, headline, time when supplied, safe excerpt/summary, and an external full-article link.
- [ ] Render absent publication time or scope as unavailable rather than fabricating a value.
- [ ] Implement and test cursor pagination.
- [ ] Show stale, partial, empty, provider-unavailable, rate-limited, and retryable states honestly.
- [ ] Add a visible “publisher context, not an Amanah classification” disclosure.

Acceptance:

- A deployed signed-in user sees at least one record ingested from the selected reviewed feed.
- Refreshing or repeating ingestion does not create duplicate articles.
- No news response or card contains a hate classification.
- A failed feed produces coverage/unavailable information rather than a zero or fixture substitution.

### 4. Activate Gemini safely

References: backend `B-S13`–`B-S15`, `B-S25`, `B-S26`; gates
`BE-GATE-SEC-07`, `BE-GATE-TEST-07`; [`adr/0009-gemini-boundary.md`](./adr/0009-gemini-boundary.md).

- [ ] Choose the exact Gemini model and record its name in environment documentation.
- [ ] Store `GEMINI_API_KEY` only in server/CI secret stores.
- [ ] Configure timeout, retry, input/output, per-run, and daily token limits.
- [ ] Confirm only permitted synthetic/redacted data classes may leave the service.
- [ ] Run the frozen AI evaluation workflow against the chosen model.
- [ ] Resolve schema, citation, numeric, benign-Muslim false-positive, counterspeech, ambiguity, causality, injection, and abstention failures.
- [ ] Run one staging text classification on synthetic content.
- [ ] Run one grounded assistant query against a stored fact bundle.
- [ ] Verify every quantitative statement cites an immutable stored fact and the model does not calculate authoritative metrics.
- [ ] Verify missing key, quota, timeout, invalid output, and budget exhaustion produce an unavailable/deferred state without breaking deterministic metrics.
- [ ] Record model, prompt, taxonomy, and data versions in the displayed result or associated report.

Acceptance:

- The browser never calls Gemini directly.
- A deployed authenticated assistant query returns a cited answer or a typed refusal.
- Frozen AI evals pass at the accepted thresholds without an invented accuracy claim.

### 5. Activate one reviewed open datapack

References: backend `B-S9A`, `B-S12.8`, `B-S21.10`; frontend datapack
requirements in `F-S2`, `F-S5`–`F-S8`; gates `BE-GATE-SEC-11`,
`BE-GATE-TEST-11`, `BE-GATE-DOC-11`.

- [ ] Select one English-language datapack appropriate for the hackathon demonstration.
- [ ] Confirm its license, permitted uses, redistribution limits, and retention requirements.
- [ ] Keep the downloaded dataset out of Git unless its reviewed license and repository data policy explicitly allow the exact artifact.
- [ ] Create a reviewed manifest recording provider, name, version, landing page, license, permitted use, retrieval time, SHA-256, schema mapping, row identity, limit, approval, and approver.
- [ ] Create a dataset card describing sampling, label meaning, limitations, known biases, and that original labels are not Amanah predictions.
- [ ] Add a stable manifest ID and repository-safe paths to [`../config/datapacks.example.yml`](../config/datapacks.example.yml).
- [ ] Set `is_enabled: true` only after the review is complete.
- [ ] Run the import dry-run and verify approval, hash, encoding, and schema checks.
- [ ] Import into staging PostgreSQL.
- [ ] Repeat the import and prove package/row idempotency.
- [ ] Run Gemini classification separately from dataset annotation import.
- [ ] Verify public source/platform is `N/A` and dataset provenance remains separate.
- [ ] Show provider, dataset name/version, license, landing page, import coverage, and sampling limitation in the live demo surface.
- [ ] Do not combine the datapack stratum with live RSS/source coverage into a prevalence claim.

Acceptance:

- One approved manifest ID completes import, classification, aggregation, and provenance display.
- A changed file hash, unapproved manifest, bad mapping, traversal path, or duplicate row is safely refused or handled as specified.

### 6. Connect assisted platform reporting

References: backend `B-S18`; frontend `F-S11`, `F-S14`, `F-S21.7`;
reconciliation `G9`; reporting requirements in [`spec.md`](./spec.md).

- [ ] Replace `prepareReportDraft`'s live `501` stub.
- [ ] Read policy candidates from `POST /v1/items/{id}/policy-analysis`.
- [ ] Show uncertainty, official policy link, policy version, and last-reviewed date.
- [ ] Require explicit policy/version confirmation.
- [ ] Let the user review and copy the bounded evidence summary and suggested wording.
- [ ] Save the prepared report through `POST /v1/prepared-reports`.
- [ ] Show the saved report in the authenticated user's Contributions history.
- [ ] Let the owner record manual submission or an outcome through `PATCH /v1/prepared-reports/{id}`.
- [ ] Keep official-form reporting and allow-listed email-style drafts distinct as required by reconciliation `G9`.
- [ ] Never automate submission, target an arbitrary address/URL, or claim platform acknowledgement.
- [ ] Test ownership, stale policy versions, low confidence, rate limiting, idempotency, safe external links, and absence of network side effects.

Acceptance:

- A demo user can prepare and save one report, then see it in their history.
- Another base user cannot read or update that report.
- No server or browser request submits the report to a platform.

### 7. Connect research reports and export

References: backend `B-S20`; frontend `F-S16`, `F-S20.4`;
[`resource-report-governance.md`](./resource-report-governance.md).

- [ ] Replace the inert research-report controls and mock snapshot list.
- [ ] Send supported dashboard/report filters to `POST /v1/research-reports`.
- [ ] Read the authorized immutable snapshot from `GET /v1/research-reports/{id}`.
- [ ] Render scope, dates, sources, coverage, denominators, findings, citations, methodology, model disclosure, versions, and limitations.
- [ ] Connect aggregate CSV download.
- [ ] Add print styles and enable browser Print/Save as PDF.
- [ ] Redact harmful content and personal identifiers by default.
- [ ] Test owner/reviewer authorization, cross-user denial, filter fidelity, immutable ready snapshots, coverage gaps, redaction, CSV schema, and print layout.

Acceptance:

- A demo user creates one real snapshot, downloads its aggregate CSV, and opens a print-ready report.
- The report states exactly which live, datapack, and fixture inputs it contains.

### 8. Implement authenticated image upload and classification

References: backend `B-S26`; reconciliation `G8`;
[`adr/0007-research-image-corpus.md`](./adr/0007-research-image-corpus.md);
[`synthetic-image-datapack.md`](./synthetic-image-datapack.md).

- [ ] Define an authenticated multipart upload contract and update `spec.md`, OpenAPI, contract tests, and frontend schemas together.
- [ ] Accept one bounded JPEG, PNG, or WebP image; document the exact size and dimension limits.
- [ ] Validate MIME from bytes, reject malformed/polyglot/decompression-bomb files, and do not trust the filename.
- [ ] Remove or avoid retaining EXIF metadata and other unnecessary personal metadata.
- [ ] Calculate SHA-256 and enforce a documented duplicate policy.
- [ ] Store bytes in a private first-party object-storage bucket, never base64 in PostgreSQL.
- [ ] Replace use of the Supabase JWT signing secret as a Storage credential with a dedicated server-only provider credential.
- [ ] Replace custom HMAC URLs with signed URLs created through the official Storage API, or serve the object through an authenticated backend stream.
- [ ] Store owner, path, hash, MIME, byte size, timestamps, retention state, and classification references in PostgreSQL.
- [ ] If the current schema cannot represent a user upload safely, obtain explicit authorization before adding a migration.
- [ ] Fetch the stored bytes server-side and classify through the controlled Gemini boundary.
- [ ] Keep user upload, dataset annotation, model prediction, and human review as separate concepts.
- [ ] Connect the frontend file picker to the multipart route; remove the filename/size-only fixture behavior in the live path.
- [ ] Apply the PA-01 image-display preference to the upload preview and returned
  result, with images visible by default and an accessible per-image Show/Hide override.
- [ ] Define demo retention and deletion behavior for user uploads.
- [ ] Add rate limits and tests for anonymous denial, ownership, wrong MIME, oversized body, malformed image, metadata stripping, duplicate hash, missing object, signed-URL expiry, Gemini failure, logging redaction, and deletion.

Acceptance:

- An authenticated demo user uploads one safe synthetic test image, receives a real Gemini classification, refreshes the page, and can still read only their authorized result.
- Image bytes, prompts, signed URLs, and harmful OCR are absent from logs and errors.
- Anonymous and cross-user access are denied.

### 9. Complete the live frontend contracts needed by the selected features

References: frontend `F-S21`; reconciliation `G1`–`G9`;
[`../apps/web/todo.md`](../apps/web/todo.md).

- [ ] Complete `F-S21.1` bearer-token handling.
- [ ] Complete `F-S21.2` dashboard reconciliation to the extent required for fact bundles, reports, and honest fixture/live labels.
- [ ] Complete `F-S21.3` item reconciliation for reportable item selection and datapack provenance.
- [ ] Complete `F-S21.4` filter reconciliation for reports and datapack/news views.
- [ ] Complete `F-S21.5` deployed News contract verification.
- [ ] Complete `F-S21.7` assisted-report integration.
- [ ] Add and complete the image-upload reconciliation item missing from the current frontend TODO.
- [ ] Split the main bundle below the Vite warning if it remains above 500 kB after the selected routes are built.
- [ ] Hide or visibly label every unimplemented control; no selected path may end in a deliberate `501`.

Acceptance:

- News, assistant, reports, and image upload use validated live responses.
- Mock pages remain coherent and explicitly labelled.

### 10. Apply the partner UI and collaboration adjustments

References: partner adjustment register `PA-01`–`PA-06` above;
[`spec.md`](./spec.md); [`adr/0004-insight-discussion.md`](./adr/0004-insight-discussion.md);
[`adr/0007-research-image-corpus.md`](./adr/0007-research-image-corpus.md);
frontend `F-S18`–`F-S20`.

- [ ] Obtain and record the governing approvals for PA-01 and PA-05 before code changes.
- [ ] Implement the persisted global image-display preference and per-image override from PA-01.
- [ ] Remove the unscoped Image Evidence section from the Insights list under PA-02.
- [ ] Replace the fixed nine-second entry hold with request-driven readiness under PA-03.
- [ ] Add the explicit Overview → created insight → all Insights navigation under PA-04.
- [ ] Implement the approved reply/attachment contract on both viewer and machine-generated insights under PA-05.
- [ ] Create and verify the reviewer-focused root README and full-stack deployment documentation under PA-06.
- [ ] Update API contracts, migrations when explicitly authorized, OpenAPI, tests,
  diagrams, ADRs, TODOs, and runbooks together for every accepted adjustment.

Acceptance:

- Every adjustment has either passed its own acceptance checks or is explicitly
  removed from hackathon scope with a recorded product decision.
- No page-local mock setting is presented as a persisted application preference.
- The accepted ADR and specification set matches the implemented media and
  attachment behavior.

### 11. Run security, test, and documentation gates

References: all cross-cutting gates in [`backend-todo.md`](./backend-todo.md)
and [`frontend-todo.md`](./frontend-todo.md); [`architecture/backend-threat-model.md`](./architecture/backend-threat-model.md).

- [ ] Update the threat model for multipart image upload, private object storage, signed URLs, and the hybrid provider.
- [ ] Complete backend security gates `BE-GATE-SEC-01`–`BE-GATE-SEC-11`.
- [ ] Complete backend testing gates `BE-GATE-TEST-01`–`BE-GATE-TEST-12`.
- [ ] Complete backend documentation gates `BE-GATE-DOC-01`–`BE-GATE-DOC-12`.
- [ ] Complete the applicable frontend security, testing, accessibility, and documentation gates.
- [ ] Run all backend unit, contract, integration, migration, constraint, and RLS tests against disposable PostgreSQL.
- [ ] Run frontend unit/component tests, lint, type check, format check, build, accessibility checks, and selected E2E paths.
- [ ] Run dependency, secret, forbidden-file, and bundle scans.
- [ ] Complete the `AGENTS.md` adversarial review and resolve or explicitly track every numbered finding.
- [ ] Verify the Qur'anic translations noted as a human task in [`frontend-backend-reconciliation.md`](./frontend-backend-reconciliation.md) against an authoritative printed or publisher copy.
- [ ] Do not check a gate merely because a test file exists; record the command/environment and result.

Acceptance:

- No required test is skipped to obtain a pass.
- The 401 previously skipped PostgreSQL-backed tests execute in CI or a dedicated scratch database.
- All remaining accepted risks are written, bounded, and approved for the demo.

### 12. Deploy and prove the production demo

References: backend `B-S21`, `B-S22`, `B-S23`; [`runbooks/deployment.md`](./runbooks/deployment.md);
[`runbooks/operations.md`](./runbooks/operations.md); [`../render.yaml`](../render.yaml);
[`../netlify.toml`](../netlify.toml); [`../.github/workflows/etl.yml`](../.github/workflows/etl.yml).

- [ ] Commit and merge the reviewed implementation through a pull request; do not deploy uncommitted workspace state.
- [ ] Provision separate staging and production Supabase projects and credentials.
- [ ] Configure exact frontend origins and authentication redirect/recovery URLs.
- [ ] Apply migrations through the documented one-off/pre-deploy process, never application startup.
- [ ] Deploy the backend through Render and verify `/healthz` and `/readyz`.
- [ ] Deploy the frontend through Netlify and verify security headers and SPA routing.
- [ ] Configure server-only database, Supabase, Storage, encryption, and Gemini secrets.
- [ ] Configure only browser-safe `VITE_*` values in Netlify.
- [ ] Create the protected GitHub `etl-production` environment and reviewed variables/secrets.
- [ ] Synchronize configuration, dry-run fixture/news/datapack inputs, then run the bounded accepted imports.
- [ ] Run the deployed smoke command with a short-lived demo access token.
- [ ] Manually verify anonymous denial for every `/v1` route and selected UI route.
- [ ] Manually complete the News, assistant, datapack, platform-report, research-report, and image-upload demo journeys.
- [ ] Verify logs contain safe IDs, counts, metrics, and error codes only.
- [ ] Prepare fixture fallback, rollback, compromised-secret, Gemini-failure, provider-outage, and missing-key procedures.
- [ ] Freeze features after acceptance; fix blockers only.

Acceptance:

- Backend `B-S23.10` and the applicable cross-cutting gates have recorded evidence.
- A fresh invited demo user can complete the selected real journeys in the deployed environment.
- The same rehearsed journey can be completed twice without duplicate imports, reports, or uploads.

## Production demo acceptance script

Run this exact journey before the presentation and once again shortly before
judging:

1. Open the public marketing page without a session and confirm no product API call occurs.
2. Open a protected route and confirm redirect to login.
3. Sign in with the invited demo user and refresh the page to prove session restoration.
4. Open News and show one article ingested from the selected reviewed RSS feed.
5. Point out that News is publisher context and has no Amanah hate classification.
6. Open the datapack view and show `N/A` source/platform plus separate dataset provenance and sampling limitations.
7. Ask one grounded Gemini starter question and show its citations, limitations, and data scope.
8. Prepare one platform report, explicitly select a policy, save it, and show that Amanah did not submit it.
9. Generate one research-report snapshot and open its CSV and print-ready view.
10. Upload one safe synthetic image, show the unblurred default, enable blur in Settings, and verify Explorer/Review update immediately.
11. Start an insight from an Overview figure, show the stored insight, then use `View all insights` to find it in the list.
12. Confirm the Insights list has no unrelated image feed.
13. Add an authorized note/attachment to a machine-generated insight and verify its private access behavior.
14. Open one mock surface and show the persistent fixture/mock label.
15. Log out and confirm protected data is no longer reachable.

## Final go/no-go checklist

The demo is a **go** only when all boxes below are checked:

- [ ] News is live, authenticated, deduplicated, paginated, and never classified as hate.
- [ ] Gemini performs a real server-side call and passes the accepted evals.
- [ ] One reviewed open datapack is imported with complete provenance and separately classified.
- [ ] Assisted platform reporting persists a real prepared report without external submission.
- [ ] Research-report snapshot, CSV, and print/PDF path work.
- [ ] Image upload stores bytes privately and returns a real server-side Gemini classification.
- [ ] Images default to visible, the persisted blur preference applies across approved surfaces, and per-image controls remain accessible.
- [ ] The Insights list contains no unrelated image feed.
- [ ] Overview-created insights have a clear route back to the full Insights list.
- [ ] Approved replies/attachments work on viewer and machine-generated insights with private access and retention controls.
- [ ] Loading duration follows real authentication/API readiness and ends in a retryable error when readiness fails.
- [ ] Supabase authentication and bearer-token handling work after refresh and expiry.
- [ ] Every mock surface is visibly labelled and no live failure silently becomes a fixture.
- [ ] Real PostgreSQL, security, AI, secret, dependency, build, and deployed smoke gates pass.
- [ ] The root reviewer README and full-stack deployment runbook are complete and verified.
- [ ] Rollback and presentation fallback material are ready.
- [ ] [`backend-todo.md`](./backend-todo.md), [`frontend-todo.md`](./frontend-todo.md), and [`../apps/web/todo.md`](../apps/web/todo.md) match the deployed state.
