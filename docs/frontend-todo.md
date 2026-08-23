# Project Amanah — Frontend Todo Checklist

**Source of truth:** [`spec.md`](./spec.md)  
**Implementation plan:** [`frontend-implementation-plan.md`](./frontend-implementation-plan.md)  
**Agent rules:** [`AGENTS.md`](./AGENTS.md) and applicable files under [`rules/`](./rules/)  
**Track:** Frontend

Use this checklist in Step ID order. A parent step is complete only when its child checks and applicable cross-cutting gates are complete. Preserve working code, keep each change reviewable, and record any intentionally deferred check with a reason.

## TRACK: frontend

### Milestone 1 — Frontend foundation and contracts

- [ ] **F-S1 — Audit and scaffold the frontend foundation**
  - [ ] **F-S1.1** Read `spec.md`, `AGENTS.md`, `rules/general.md`, `rules/frontend.md`, `rules/testing.md`, `rules/security.md`, and `rules/documentation.md`.
  - [ ] **F-S1.2** Inventory existing files, scripts, dependencies, and user changes before scaffolding.
  - [ ] **F-S1.3** Establish or reconcile the React/Vite/TypeScript application structure without replacing working code.
  - [ ] **F-S1.4** Configure pinned dependencies and scripts for dev, build, lint, type check, format, and tests.
  - [ ] **F-S1.5** Add a minimal render smoke test that can fail meaningfully.
  - [ ] **F-S1.6** Document and verify the frontend setup commands.

- [ ] **F-S2 — Define API contracts and the fixture provider**
  - [ ] **F-S2.1** Derive dashboard, item, filter, resource, contribution, and error response types from `spec.md`.
  - [ ] **F-S2.2** Add Zod validation at the API-provider boundary and infer TypeScript types from schemas.
  - [ ] **F-S2.3** Define one provider interface shared by fixture and live implementations.
  - [ ] **F-S2.4** Add coherent synthetic/redacted fixtures with explicit `fixture` metadata.
  - [ ] **F-S2.5** Reject malformed enums, timestamps, rates without denominators, and missing AI/review states in contract tests.
  - [ ] **F-S2.6** Ensure provider selection never silently presents fixtures as live data.
  - [ ] **F-S2.7** Model datapack items with source/platform `N/A` and separate provider/name/version/license/import provenance.

- [ ] **F-S3 — Build routes, global providers, authentication boundary, and the application shell**
  - [ ] **F-S3.1** Add the marketing/auth-entry, authenticated, reviewer, and admin route map from `spec.md`.
  - [ ] **F-S3.2** Add lazy-loaded placeholder pages where feature implementation belongs to later steps.
  - [ ] **F-S3.3** Add global query, API-provider, and application-context providers without duplicating state.
  - [ ] **F-S3.4** Implement semantic desktop/mobile navigation, footer, 404 route, and active-route behavior.
  - [ ] **F-S3.5** Establish Amanah brand tokens and base styles without building a speculative component library.
  - [ ] **F-S3.6** Restore Supabase session state before resolving protected routes and add a deny-by-default application route guard.
  - [ ] **F-S3.7** Keep only `/`, auth entry/callback/recovery, and required static assets unauthenticated.
  - [ ] **F-S3.8** Test that every application route redirects anonymous users without issuing protected API requests.

### Milestone 2 — Marketing and authenticated discovery experience

- [ ] **F-S4 — Implement the public marketing homepage**
  - [ ] **F-S4.1** Explain the problem, intended research audience, monitored-sample value, and product purpose in the first viewport.
  - [ ] **F-S4.2** Make “Sign in to dashboard” the primary action and Sign up secondary when enabled.
  - [ ] **F-S4.3** Explain the AI/human-review boundary, responsible use, and key limitations.
  - [ ] **F-S4.4** Link Login and Sign up; describe Resources and Methodology without bypassing their authentication boundary.
  - [ ] **F-S4.5** Explain Amanah as trust/responsibility without presenting the app as a religious authority.
  - [ ] **F-S4.6** Test required content, disclosures, auth links, semantics, and responsive behavior.
  - [ ] **F-S4.7** Prove the marketing page renders without a session and never calls a protected product API.

- [ ] **F-S5 — Implement dashboard coverage, headlines, and metric summaries**
  - [ ] **F-S5.1** Fetch dashboard data through the validated provider boundary only after session validation.
  - [ ] **F-S5.2** Render freshness, observation window, monitored sources, coverage, and warnings before or beside metrics.
  - [ ] **F-S5.3** Render current major headlines before deeper analytics.
  - [ ] **F-S5.4** Render observed, Muslim-related, likely anti-Muslim, likely-hate rate, reviewed, and confirmed metrics.
  - [ ] **F-S5.5** Expose numerator, denominator, date window, source scope, and data mode for every rate.
  - [ ] **F-S5.6** Render missing history as unavailable/gaps rather than zero.
  - [ ] **F-S5.7** Test live, fixture, stale, partial, and missing-data presentations.
  - [ ] **F-S5.8** Present datapack/import coverage separately from live connector freshness.
  - [ ] **F-S5.9** Disclose purposive/enriched seed sampling and keep enriched, boundary/control, and ordinary-monitoring strata distinct from platform-prevalence claims.

- [ ] **F-S6 — Add filters, sorting, and URL-backed state**
  - [ ] **F-S6.1** Implement date, content-kind, source/platform, Dataset, explicit geography, topic/narrative, severity, review-state, and confidence filters.
  - [ ] **F-S6.2** Implement newest, oldest, highest-confidence, lowest-confidence, and highest-severity sorting where supported.
  - [ ] **F-S6.3** Encode filter and sort state in URL query parameters.
  - [ ] **F-S6.4** Add active filter chips and a complete Reset action.
  - [ ] **F-S6.5** Restore state correctly through browser Back and Forward navigation.
  - [ ] **F-S6.6** Reject/remove unsupported URL values visibly rather than broadening a query silently.
  - [ ] **F-S6.7** Test parsing, serialization, provider queries, reset, and navigation restoration.
  - [ ] **F-S6.8** Verify datapack records filter as source/platform `N/A` while Dataset uses provider/name/version.

- [ ] **F-S7 — Add item cards and transparent AI states**
  - [ ] **F-S7.1** Implement explicit news and social item-card variants.
  - [ ] **F-S7.2** Show High, Medium, or Low confidence on every AI-classified item card.
  - [ ] **F-S7.3** Show Model only, Pending review, Confirmed, Corrected, Disputed, and Needs context states distinctly.
  - [ ] **F-S7.4** Use text/non-color cues and accessible labels for confidence and review state.
  - [ ] **F-S7.5** Redact harmful excerpts by default and omit author identifiers from base-role projections.
  - [ ] **F-S7.6** Use stable item IDs as keys and link cards to item detail.
  - [ ] **F-S7.7** Test every confidence/review combination and redaction behavior.
  - [ ] **F-S7.8** Display source/platform `N/A` plus a separate base-role-safe Dataset label on datapack cards.

- [ ] **F-S8 — Implement authenticated item detail and content-safety controls**
  - [ ] **F-S8.1** Implement the item route and typed detail query.
  - [ ] **F-S8.2** For news, show metadata, Amanah summary/insight, tags, related context, and a full-publisher-article link.
  - [ ] **F-S8.3** For social content, show redacted context, classification, exact score, confidence tier, rationale, model version, and review state.
  - [ ] **F-S8.4** Add a content warning and deliberate reveal control with focus-safe behavior.
  - [ ] **F-S8.5** Add authenticated action entry points for dispute and assisted reporting.
  - [ ] **F-S8.6** Display “Comments coming soon” without fake input, users, counts, or engagement.
  - [ ] **F-S8.7** Test missing items, source-link safety, content reveal, and both item variants.
  - [ ] **F-S8.8** Show datapack provider, package, version, license, and landing-page provenance separately from source/platform `N/A`.
  - [ ] **F-S8.9** Show a base-role-safe sampling-purpose/stratum disclosure for registry-backed items without exposing internal registry keys.

### Milestone 3 — Authentication completion and onboarding

- [ ] **F-S9 — Complete authentication UX and safe return routing**
  - [ ] **F-S9.1** Build on the F-S3 session boundary without creating a second authentication store.
  - [ ] **F-S9.2** Complete Login, Sign up, Logout, optional recovery, callback, and expired-session behavior.
  - [ ] **F-S9.3** Keep only the marketing homepage and required authentication routes available anonymously.
  - [ ] **F-S9.4** Preserve a validated internal application destination through authentication and default to `/dashboard`.
  - [ ] **F-S9.5** Prevent external/open redirect destinations.
  - [ ] **F-S9.6** Handle pending, expired-session, generic authentication failure, and logout states.
  - [ ] **F-S9.7** Test marketing-only anonymous access, denial of every application route, protected deep-link return, callback validation, default dashboard return, and logout.

- [ ] **F-S10 — Implement first-sign-in onboarding**
  - [ ] **F-S10.1** Explain dashboard navigation, coverage, monitored-sample metrics, confidence tiers, and review labels.
  - [ ] **F-S10.2** Explain filters and the primary submission, dispute, assisted-reporting, and PDF actions.
  - [ ] **F-S10.3** Provide Back, Next, Skip, and Finish with correct keyboard/focus behavior.
  - [ ] **F-S10.4** Persist completion or skip through the profile API.
  - [ ] **F-S10.5** Handle persistence failure without pretending onboarding was saved.
  - [ ] **F-S10.6** Return the user to the preserved destination after completion or skip.
  - [ ] **F-S10.7** Test first-time display, persistence, keyboard flow, and failure recovery.

### Milestone 4 — User contributions and reporting actions

- [ ] **F-S11 — Implement Your Contributions**
  - [ ] **F-S11.1** Add typed variants for URL submissions, classification disputes, and prepared platform reports.
  - [ ] **F-S11.2** Render type, title/URL, created time, update time, status, user-safe event, and destination.
  - [ ] **F-S11.3** Implement contribution detail and cursor pagination when present.
  - [ ] **F-S11.4** Handle loading, empty, partial, unauthorized, and missing contribution states.
  - [ ] **F-S11.5** Ensure the UI never attempts to show another user’s contribution data.
  - [ ] **F-S11.6** Test each contribution variant and state.

- [ ] **F-S12 — Implement URL submission**
  - [ ] **F-S12.1** Add a labelled form accepting one public HTTP(S) URL.
  - [ ] **F-S12.2** Add client-side UX validation while leaving security validation to the backend.
  - [ ] **F-S12.3** Generate/send an idempotency key for the mutation.
  - [ ] **F-S12.4** Show Processing and link to the contribution after success.
  - [ ] **F-S12.5** Handle duplicate, unsupported, inaccessible, rejected, rate-limited, expired-session, and retryable states distinctly.
  - [ ] **F-S12.6** Preserve unsent input across a retryable failure without logging it.
  - [ ] **F-S12.7** Test anonymous gating, validation, success, duplicate, retry, and contribution linkage.

- [ ] **F-S13 — Implement classification disputes**
  - [ ] **F-S13.1** Add the authenticated “This is not hateful” action on eligible items.
  - [ ] **F-S13.2** Allow bounded optional context and explain that manual review follows.
  - [ ] **F-S13.3** Use idempotency and link to an existing open dispute where returned.
  - [ ] **F-S13.4** Keep the original model result unchanged while review is pending.
  - [ ] **F-S13.5** Display Pending review after success and link the contribution.
  - [ ] **F-S13.6** Display the final review outcome in contribution detail.
  - [ ] **F-S13.7** Test auth, success, duplicate-open, retry, and status transitions.

- [ ] **F-S14 — Implement assisted platform reporting**
  - [ ] **F-S14.1** Load candidate policies through the authenticated API.
  - [ ] **F-S14.2** Present matches as uncertain with official URL, version, and last-reviewed date.
  - [ ] **F-S14.3** Require the user to select/confirm the relevant policy.
  - [ ] **F-S14.4** Show evidence summary, suggested wording, safe Copy action, and official reporting link/instructions.
  - [ ] **F-S14.5** Display anti-brigading and no-automatic-submission guidance.
  - [ ] **F-S14.6** Save the prepared report and show it in Contributions.
  - [ ] **F-S14.7** Allow later Submitted and platform-outcome updates without claiming verification.
  - [ ] **F-S14.8** Test policy selection, persistence, link safety, no external side effect, and outcome transitions.

### Milestone 5 — Resources, reports, and declared mocks

- [ ] **F-S15 — Implement resources and coming-soon surfaces**
  - [ ] **F-S15.1** Render reviewed resources with organization, category, country/scope, summary, URL, and last-reviewed date.
  - [ ] **F-S15.2** Add resource filtering with clear active scope and Reset.
  - [ ] **F-S15.3** Open external resources safely and avoid implying endorsement.
  - [ ] **F-S15.4** Implement `/forum` as a clear Coming soon page.
  - [ ] **F-S15.5** Verify item pages show Comments coming soon only.
  - [ ] **F-S15.6** Test filtering, empty states, external links, and absence of fabricated community data.

- [ ] **F-S16 — Implement research report preview and PDF workflow**
  - [ ] **F-S16.1** Inherit active dashboard filters into report creation.
  - [ ] **F-S16.2** Render scope, dates, sources, coverage, denominators, findings, citations, methodology, model disclosure, and limitations.
  - [ ] **F-S16.3** Save/resolve the backend snapshot before presenting a final report.
  - [ ] **F-S16.4** Redact harmful content and personal identifiers by default.
  - [ ] **F-S16.5** Add print styles for browser Print/Save as PDF with accessible hierarchy and controlled page breaks.
  - [ ] **F-S16.6** Keep the preview usable and provide retry guidance if snapshot/PDF preparation fails.
  - [ ] **F-S16.7** Test filter fidelity, required disclosures, authorization, redaction, and print rendering.

- [ ] **F-S17 — Add the declared social-sharing mock**
  - [ ] **F-S17.1** Add sharing entry points only to approved report, news, and statistic surfaces.
  - [ ] **F-S17.2** Label all controls and dialogs Demo or Coming soon before any apparent completion.
  - [ ] **F-S17.3** Do not request social credentials or call external publishing/compose APIs.
  - [ ] **F-S17.4** Do not expose sensitive/harmful content in a mock preview.
  - [ ] **F-S17.5** Test mock labelling and prove that no external side effect occurs.

### Milestone 6 — Resilience, accessibility, and demo readiness

- [ ] **F-S18 — Complete state and recovery coverage**
  - [ ] **F-S18.1** Inventory every P0 route/query/mutation against loading, empty, partial, stale, fixture, offline, unauthorized, rate-limited, and retryable states.
  - [ ] **F-S18.2** Add shared state primitives only where at least three real consumers justify them.
  - [ ] **F-S18.3** Add an application error boundary for unexpected render failures.
  - [ ] **F-S18.4** Keep typed expected API errors in normal UI flow.
  - [ ] **F-S18.5** Never silently replace live data with fixtures.
  - [ ] **F-S18.6** Preserve safe user input across retryable mutation/auth failures.
  - [ ] **F-S18.7** Test each state and its recovery action.

- [ ] **F-S19 — Complete accessibility, responsive, and print QA**
  - [ ] **F-S19.1** Complete all P0 flows by keyboard only.
  - [ ] **F-S19.2** Verify visible focus, modal focus trap/return, semantic headings, form labels, and accessible names.
  - [ ] **F-S19.3** Provide accessible chart summaries/equivalent data and non-color state cues.
  - [ ] **F-S19.4** Verify 375, 768, 1024, and 1440 px layouts.
  - [ ] **F-S19.5** Respect reduced-motion and high-contrast preferences.
  - [ ] **F-S19.6** Verify print hierarchy, citations, URLs, page breaks, and hidden interactive chrome.
  - [ ] **F-S19.7** Run automated accessibility checks and record required manual results.

- [ ] **F-S20 — Add end-to-end demo coverage and freeze**
  - [ ] **F-S20.1** Automate marketing homepage → authentication → onboarding → dashboard → filter → item.
  - [ ] **F-S20.2** Automate anonymous protected deep link → authentication → validated intended destination.
  - [ ] **F-S20.3** Automate URL contribution, classification dispute, and prepared-report paths.
  - [ ] **F-S20.4** Automate research-report preview and print/PDF-ready path.
  - [ ] **F-S20.5** Assert fixture/live/stale labels and prevent production-provider calls.
  - [ ] **F-S20.6** Document demo startup, fixture fallback, and known limitations.
  - [ ] **F-S20.7** Run lint, format check, type check, unit/component tests, accessibility checks, production build, and E2E tests.
  - [ ] **F-S20.8** Assert every application route denies anonymous access without issuing protected API requests.
  - [ ] **F-S20.9** Freeze feature scope and fix acceptance blockers only.

## Cross-cutting gates

### Security review

- [ ] **FE-GATE-SEC-01** Verify no provider, Gemini, Supabase service-role, or other secret is present in browser code, fixtures, logs, or committed environment files.
- [ ] **FE-GATE-SEC-02** Verify route guards are UX only, every product API still requires backend authentication, and the UI handles 401/403 responses safely.
- [ ] **FE-GATE-SEC-03** Verify intended-destination restoration cannot create an open redirect.
- [ ] **FE-GATE-SEC-04** Verify external content is escaped and no unreviewed `dangerouslySetInnerHTML` path exists.
- [ ] **FE-GATE-SEC-05** Verify source/resource/reporting links use safe protocols and appropriate external-link handling.
- [ ] **FE-GATE-SEC-06** Verify harmful content and personal identifiers are redacted/concealed by default.
- [ ] **FE-GATE-SEC-07** Verify social-reporting/sharing mocks perform no external submission or sensitive-data disclosure.
- [ ] **FE-GATE-SEC-08** Complete an adversarial review using the `AGENTS.md` persona and resolve or explicitly track every numbered finding.
- [ ] **FE-GATE-SEC-09** Verify the marketing page cannot fetch or render dashboard, item, news, methodology, resource, report, connection, reviewer, or admin data.

### Testing gate

- [ ] **FE-GATE-TEST-01** All frontend unit and component tests pass.
- [ ] **FE-GATE-TEST-02** API/fixture contract validation tests pass.
- [ ] **FE-GATE-TEST-03** Negative auth, validation, rate-limit, retry, stale, fixture, and redaction tests pass.
- [ ] **FE-GATE-TEST-04** Automated accessibility checks pass for every P0 route.
- [ ] **FE-GATE-TEST-05** Keyboard-only manual checks pass for every P0 flow.
- [ ] **FE-GATE-TEST-06** Responsive checks pass at 375, 768, 1024, and 1440 px.
- [ ] **FE-GATE-TEST-07** Print/report layout is visually verified in Chromium.
- [ ] **FE-GATE-TEST-08** Production build and deterministic E2E suite pass.
- [ ] **FE-GATE-TEST-09** No existing tests were deleted, weakened, disabled, or skipped to obtain a pass.
- [ ] **FE-GATE-TEST-10** Anonymous-access tests cover every product route plus direct API denial, with no protected request emitted before session restoration completes.

### Documentation gate

- [ ] **FE-GATE-DOC-01** Frontend README commands are accurate and verified.
- [ ] **FE-GATE-DOC-02** Marketing/auth-entry and protected-route documentation match the implementation and environment configuration.
- [ ] **FE-GATE-DOC-03** API contract changes are synchronized with backend OpenAPI and contract tests.
- [ ] **FE-GATE-DOC-04** Fixture, live, fallback, stale, mock, and coming-soon behavior is documented accurately.
- [ ] **FE-GATE-DOC-05** Accessibility and manual QA notes are recorded.
- [ ] **FE-GATE-DOC-06** Demo instructions and known limitations reflect the deployed build.
- [ ] **FE-GATE-DOC-07** Any divergence from `spec.md`, the plan, or `/rules` has explicit written approval and rationale.
