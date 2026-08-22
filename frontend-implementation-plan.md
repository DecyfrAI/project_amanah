# Project Amanah — Frontend Blueprint and Code-Generation Prompt Pack

**Source of truth:** [`spec.md`](./spec.md)  
**Track owner:** Frontend  
**Target:** React + Vite + TypeScript web application deployed to Netlify  
**Companion:** [`backend-implementation-plan.md`](./backend-implementation-plan.md)

## How to use this file

Execute steps in order. Each step is intended to fit in one short coding session or reviewable PR. The frontend MUST be built against one typed API boundary: fixtures and live HTTP responses implement the same contracts.

Every code-generation prompt below requires the coding LLM to read the applicable files in `/rules` before it inspects or changes code. Instructions in `/rules` and `spec.md` are binding. If they conflict, stop and ask for direction rather than silently choosing one.

## 1. Project Blueprint

- **Milestone 1: Frontend foundation and contracts**
  - **Goal:** Establish the TypeScript application, routing, design foundation, and one validated data-provider boundary without building product features prematurely.
  - **Main components:** Vite app, router, providers, design tokens, API contracts, fixture provider, test harness.
  - **Expected artifacts:** Runnable app shell, route map, typed contracts, safe fixtures, unit/component test setup.

- **Milestone 2: Public discovery experience**
  - **Goal:** Deliver the anonymous homepage-to-dashboard-to-item journey with current headlines, transparent monitored-sample metrics, filtering, sorting, and item-level AI transparency.
  - **Main components:** Homepage, application shell, dashboard, filters, headline/item cards, charts, item detail, content-safety controls.
  - **Expected artifacts:** Public routes, query-state handling, reusable cards, confidence/review badges, detail pages, public-state tests.

- **Milestone 3: Authentication and onboarding**
  - **Goal:** Gate contribution actions while preserving public viewing and returning users to their intended action after authentication.
  - **Main components:** Supabase session provider, login/sign-up screens, action gate, onboarding guide, protected routing.
  - **Expected artifacts:** Authentication UX, redirect restoration, onboarding persistence, route and authorization tests.

- **Milestone 4: User contributions and reporting actions**
  - **Goal:** Let registered users submit URLs, dispute classifications, prepare platform reports, and track every contribution.
  - **Main components:** Submission form, dispute form, policy-report wizard, contributions list/detail, status components.
  - **Expected artifacts:** Gated action flows, API mutations, status history, retry behavior, integration tests.

- **Milestone 5: Resources, reports, and declared mocks**
  - **Goal:** Complete researcher-facing resources and export flows while honestly presenting features that are intentionally mocked or coming soon.
  - **Main components:** Resources page, research report builder, print layout, social-share mock, forum and comments placeholders.
  - **Expected artifacts:** Resource catalog UI, report preview/PDF flow, mock labels, coming-soon routes, print tests.

- **Milestone 6: Resilience, accessibility, and demo readiness**
  - **Goal:** Make every P0 path robust across loading, empty, stale, fixture, offline, mobile, keyboard, and print contexts.
  - **Main components:** State primitives, error boundary, responsive layouts, accessibility checks, E2E suite.
  - **Expected artifacts:** Complete state coverage, WCAG-oriented validation, responsive QA, demo smoke test.

## 2. Refined Implementation Steps

- **F-S1 (Milestone 1) [frontend]: Audit and scaffold the frontend foundation.** Inspect the current workspace, preserve existing work, establish the Vite/React/TypeScript structure and test commands, and add only the dependencies required by `spec.md`. Dependencies: none.
- **F-S2 (Milestone 1) [frontend]: Define the shared frontend API contracts and fixture provider.** Create Zod-validated response types, one provider interface, synthetic/redacted fixtures, open-datapack provenance fields, and fixture contract tests. Dependencies: F-S1; backend contract names in `spec.md`.
- **F-S3 (Milestone 1) [frontend]: Build routing, providers, and the visual application shell.** Add public/protected/reviewer route groups, global providers, brand tokens, header/navigation, and placeholder pages without implementing feature content. Dependencies: F-S1–F-S2.
- **F-S4 (Milestone 2) [frontend]: Implement the public homepage.** Build the mission, intended audience, monitored-sample disclosure, responsible-use summary, and primary View dashboard action. Dependencies: F-S3.
- **F-S5 (Milestone 2) [frontend]: Implement dashboard coverage, headlines, and metric summaries.** Render the public data-freshness strip, current headlines, key monitored-sample metrics, and live/fixture/stale disclosure from the provider. Dependencies: F-S2–F-S3.
- **F-S6 (Milestone 2) [frontend]: Add public filters, sorting, and URL state.** Implement validated filter controls, including separate source/platform and Dataset filters, active chips, reset, supported sorts, query-string persistence, and back/forward restoration. Dependencies: F-S5.
- **F-S7 (Milestone 2) [frontend]: Add item cards and transparent AI states.** Render content-type-aware cards with High/Medium/Low confidence and distinct model/review states, using exact accessible text rather than color alone. Dependencies: F-S5–F-S6.
- **F-S8 (Milestone 2) [frontend]: Implement public item detail and content-safety controls.** Add news/social variants, summaries, rationale, exact score/model metadata, deliberate content reveal, publisher/source links, and comments-coming-soon. Dependencies: F-S7.
- **F-S9 (Milestone 3) [frontend]: Integrate authentication and action gating.** Add Supabase session handling, login/sign-up/logout, protected routes, and safe restoration of the intended action after authentication. Dependencies: F-S3 and backend auth configuration.
- **F-S10 (Milestone 3) [frontend]: Implement first-sign-in onboarding.** Create a skippable guide for dashboard concepts and primary actions, persist its state, and return the user to the pending destination. Dependencies: F-S9.
- **F-S11 (Milestone 4) [frontend]: Implement Your Contributions.** Build the authenticated contributions list/detail, typed contribution variants, statuses, timestamps, links, and ownership-safe error states. Dependencies: F-S9 and backend contribution endpoints.
- **F-S12 (Milestone 4) [frontend]: Implement URL submission.** Add a single-URL form, client-side UX validation, idempotent mutation, processing confirmation, duplicate/unsupported states, and contribution linkage. Dependencies: F-S11 and backend submission endpoint.
- **F-S13 (Milestone 4) [frontend]: Implement classification disputes.** Add the “This is not hateful” action, optional context, pending/final status, duplicate-open-dispute handling, and retry-safe submission. Dependencies: F-S8–F-S11 and backend dispute endpoint.
- **F-S14 (Milestone 4) [frontend]: Implement assisted platform reporting.** Build the candidate-policy review, rule confirmation, evidence/suggested-text preview, official-report link, prepared-record save, and later outcome update. Dependencies: F-S8–F-S11 and backend policy/report endpoints.
- **F-S15 (Milestone 5) [frontend]: Implement resources and coming-soon surfaces.** Build the filterable reviewed resource catalog and the honest forum/comments placeholders without fabricated engagement. Dependencies: F-S3 and backend resource endpoint.
- **F-S16 (Milestone 5) [frontend]: Implement research report preview and PDF workflow.** Inherit dashboard filters, render scope/coverage/findings/citations/limitations, save the snapshot, and provide print/save-as-PDF behavior. Dependencies: F-S6, F-S9, and backend research-report endpoints.
- **F-S17 (Milestone 5) [frontend]: Add the declared social-sharing mock.** Provide clearly labelled demo controls for reports, news, and statistics with no external side effects. Dependencies: F-S5, F-S8, F-S16.
- **F-S18 (Milestone 6) [frontend]: Complete loading, empty, error, stale, fixture, and offline states.** Apply consistent state components and error recovery across every P0 route and mutation. Dependencies: F-S4–F-S17.
- **F-S19 (Milestone 6) [frontend]: Complete accessibility, responsive, and print QA.** Fix keyboard, focus, semantic, contrast, chart-summary, 375px layout, reduced-motion, and print issues. Dependencies: F-S18.
- **F-S20 (Milestone 6) [frontend]: Add end-to-end demo coverage and freeze the frontend.** Automate the public journey, auth return, contribution, dispute/reporting, and PDF paths against deterministic fixtures, then document the demo mode. Dependencies: F-S1–F-S19.

### Coverage and sequencing verification

- **Coverage:** Every public route, gated action, declared mock, and UX-quality requirement in `spec.md` maps to at least one step.
- **Complexity ramp:** Contracts and shell precede features; read-only public views precede authentication; authentication precedes mutations; resilience follows working flows.
- **No overlaps:** Each step owns a distinct observable behavior. Shared primitives are created only when the first real consumer needs them.
- **Cross-track boundary:** F-S2 defines frontend contracts from `spec.md`; it does not invent backend schema. Live provider integration occurs through that boundary only.
- **Pass 2 result:** Dashboard state, user actions, resilience, accessibility, and E2E work have been separated into session-sized changes; no further refinement is required.

## 3. Code-Generation Prompt Pack

### Step F-S1 — Audit and scaffold the frontend foundation [frontend]

```text
You are implementing frontend step F-S1 for Project Amanah.

Mandatory first action:
- Read spec.md completely.
- Read rules/general.md, rules/frontend.md, rules/testing.md, rules/security.md, and rules/documentation.md before changing files.
- Inspect the workspace and preserve existing user work. Do not assume the repository is empty.

Context:
- This is the first frontend step.
- The target is a React/Vite/TypeScript application with short, reviewable increments.

Task:
- Audit the current frontend state and establish the minimum runnable frontend and test foundation required by spec.md.

Requirements:
- Add or reconcile the Vite/React/TypeScript structure, package scripts, formatting/lint/typecheck/test configuration, and a minimal render smoke test.
- Add only dependencies justified by the current step; pin versions according to /rules.
- Do not build product screens yet.
- Document the verified local commands in the appropriate README without duplicating spec.md.
- Run the smallest relevant checks and report exact results.
- Extend and integrate; do not rewrite working code.

Output:
- Updated/new code and configuration.
- A short summary of changes, tests run, and any discovered constraints.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S2 — API contracts and fixture provider [frontend]

```text
You are implementing frontend step F-S2 for Project Amanah.

Mandatory first action:
- Read spec.md and the current result of F-S1.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/testing.md, and rules/security.md.

Context:
- F-S1 produced the runnable frontend/test foundation.
- The app must use one typed boundary for fixture and live data.

Task:
- Define frontend response contracts and a fixture-backed provider for the public dashboard and item-detail minimum needed by later steps.

Requirements:
- Derive names and shapes from spec.md; do not create a competing API design.
- Model open-datapack records with public source/platform `N/A` plus separate dataset provider/name/version/license provenance; never substitute the dataset provider into the source field.
- Add Zod validation at the provider boundary and inferred TypeScript types.
- Provide coherent synthetic/redacted fixtures with explicit fixture metadata.
- Add contract tests that fail for malformed enums, timestamps, metrics without denominators, and missing confidence/review states.
- Keep provider selection explicit; never silently present fixtures as live.
- Do not build UI beyond a test consumer if needed.
- Extend and integrate; do not rewrite working code.

Output:
- Contracts, provider interface, fixture provider/data, and focused tests.
- A short summary of the contract decisions and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S3 — Routes, providers, and application shell [frontend]

```text
You are implementing frontend step F-S3 for Project Amanah.

Mandatory first action:
- Read spec.md and inspect F-S1–F-S2 outputs.
- Read rules/general.md, rules/frontend.md, rules/testing.md, rules/security.md, and rules/documentation.md.

Context:
- The app and validated provider boundary exist.
- Product pages have not yet been implemented.

Task:
- Build the route skeleton, global providers, brand tokens, and responsive application shell.

Requirements:
- Add every public, authenticated, reviewer, and admin route from spec.md as a lazy-loadable placeholder where appropriate.
- Create semantic header/navigation/footer and mobile navigation without inventing feature content.
- Establish tokens from the existing Amanah brand documents; avoid a generic design-system abstraction.
- Add route smoke tests, active-navigation tests, and a 404 route.
- Keep authorization enforcement as a later step; mark protected route metadata now without fake security.
- Extend and integrate; do not rewrite working code.

Output:
- Routing, providers, shell, tokens, placeholders, and tests.
- A short summary of changed routes and checks.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S4 — Public homepage [frontend]

```text
You are implementing frontend step F-S4 for Project Amanah.

Mandatory first action:
- Read spec.md, especially homepage, users, principles, and non-goals.
- Read rules/general.md, rules/frontend.md, rules/testing.md, and rules/security.md.

Context:
- F-S3 provides the public shell and route.
- The primary homepage action is View dashboard.

Task:
- Implement the public homepage as the entry point for researchers and secondary public audiences.

Requirements:
- Explain the problem, monitored-sample value, AI/human-review boundary, responsible use, and Amanah meaning without overstating capabilities.
- Make View dashboard the dominant CTA; link Resources, Methodology, Login, and Sign up.
- Use semantic sections and accessible responsive content.
- Do not show real harmful content or claim unavailable integrations are live.
- Add component tests for the primary CTA and mandatory disclosures.
- Extend and integrate; do not rewrite working code.

Output:
- Homepage components/styles/tests.
- A short summary and verification note.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S5 — Dashboard coverage, headlines, and metrics [frontend]

```text
You are implementing frontend step F-S5 for Project Amanah.

Mandatory first action:
- Read spec.md and inspect F-S2–F-S4.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/testing.md, and rules/security.md.

Context:
- Validated fixture dashboard data and the public shell exist.
- Filters and item detail come later.

Task:
- Implement the first useful public dashboard view.

Requirements:
- Render freshness/coverage before or beside metrics, then headline-first content, monitored-sample metrics, and a restrained findings summary.
- Include reviewed open-datapack/import coverage distinctly from live provider freshness.
- Disclose purposive/enriched seed sampling and keep enriched, boundary/control, and ordinary-monitoring strata visually distinct; never present the seed sample as platform prevalence.
- Every rate must expose numerator, denominator, time window, source scope, and data mode.
- Show missing history as unavailable, not zero.
- Separate data fetching from presentation and use the provider boundary.
- Add loading skeletons only for actual pending data and focused tests for metric disclosure and live/fixture/stale labels.
- Extend and integrate; do not rewrite working code.

Output:
- Dashboard query hook, coverage/headline/metric components, styles, and tests.
- A short summary and test results.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S6 — Filters, sorting, and URL state [frontend]

```text
You are implementing frontend step F-S6 for Project Amanah.

Mandatory first action:
- Read spec.md filter requirements and inspect F-S5.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/testing.md, and rules/security.md.

Context:
- The dashboard renders provider data without public controls.

Task:
- Add filter and sort controls whose state is encoded in the URL and passed through the typed provider.

Requirements:
- Support date, content kind, source/platform, Dataset, explicit geography, narrative/topic, severity, review state, confidence tier, and documented sort options.
- Source/platform MUST show `N/A` for datapack items; Dataset filters use provider/name/version separately.
- Render active chips and Reset; browser back/forward must restore state.
- Reject or remove unsupported URL values visibly rather than broadening queries silently.
- Use visible labels, native controls where practical, and keyboard-safe focus behavior.
- Add parsing/serialization unit tests and an integration test for filter-to-query behavior.
- Extend and integrate; do not rewrite working code.

Output:
- Filter/sort model, URL adapter, controls, provider integration, and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S7 — Item cards and AI transparency [frontend]

```text
You are implementing frontend step F-S7 for Project Amanah.

Mandatory first action:
- Read spec.md confidence, classification, and item requirements.
- Read rules/general.md, rules/frontend.md, rules/testing.md, and rules/security.md.

Context:
- Dashboard queries, filters, and sorting work.

Task:
- Add reusable news/social item cards with transparent AI and human-review states.

Requirements:
- Show High/Medium/Low confidence on every AI-classified card.
- Show Model only, Pending review, Confirmed, Corrected, Disputed, or Needs context distinctly using text and non-color cues.
- Keep news and social variants explicit; do not create an over-general component with many mode flags.
- Redact harmful excerpts by default and avoid author identifiers.
- For datapack items, render source/platform as `N/A` and a separate Dataset label when provenance is public-safe.
- Add accessible names, stable keys, and tests for every confidence/review state.
- Extend and integrate; do not rewrite working code.

Output:
- Item-card components, badges, redaction primitive, and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S8 — Public item detail and content safety [frontend]

```text
You are implementing frontend step F-S8 for Project Amanah.

Mandatory first action:
- Read spec.md item journeys and safety requirements.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/testing.md, and rules/security.md.

Context:
- Item cards link to the placeholder item-detail route.

Task:
- Implement public-safe news and social item detail views.

Requirements:
- News: source metadata, Amanah summary/insight, tags, related context, and full-article link; never reproduce the full article by default.
- Social: redacted preview, bounded context, classification, exact score, tier, rationale, model version, review state, and permitted source link.
- Datapack: show source/platform `N/A` plus dataset provider, package name, version, license, and landing-page provenance when public-safe.
- Registry-backed live/fixture items: show a public-safe sampling-purpose/stratum disclosure without exposing internal registry keys.
- Add deliberate reveal with content warning and focus-safe behavior.
- Show gated action entry points without implementing their mutations yet.
- Display “Comments coming soon” with no fake data or input.
- Add route/data/error/content-reveal tests.
- Extend and integrate; do not rewrite working code.

Output:
- Detail query/view components, safety controls, and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S9 — Authentication and action gating [frontend]

```text
You are implementing frontend step F-S9 for Project Amanah.

Mandatory first action:
- Read spec.md authentication/authorization requirements.
- Read rules/general.md, rules/frontend.md, rules/security.md, rules/testing.md, and rules/api.md.

Context:
- Public viewing works; gated action buttons are present.
- Supabase is the selected identity provider.

Task:
- Integrate Supabase session handling and gate actions/protected routes while keeping public routes anonymous.

Requirements:
- Add login, sign-up, logout, session restoration, and protected-route behavior.
- Preserve the intended internal destination/action through authentication; prevent open redirects.
- Do not duplicate authentication state in unrelated stores.
- Handle loading, expired session, failed login, and generic non-enumerating errors.
- Treat frontend gating as UX only; rely on backend authorization for security.
- Add tests for anonymous viewing, action redirect, safe return, and logout.
- Extend and integrate; do not rewrite working code.

Output:
- Auth provider/hooks/pages/guards and focused tests.
- A short security and verification summary.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S10 — First-sign-in onboarding [frontend]

```text
You are implementing frontend step F-S10 for Project Amanah.

Mandatory first action:
- Read spec.md onboarding journey and inspect F-S9.
- Read rules/general.md, rules/frontend.md, rules/testing.md, and rules/security.md.

Context:
- Authentication and safe return destinations work.

Task:
- Implement a skippable, persistent onboarding guide for first-time registered users.

Requirements:
- Explain dashboard navigation, coverage, monitored-sample metrics, confidence tiers, review labels, filters, and primary gated actions.
- Use a short step sequence with semantic controls, focus management, Skip, Back, Next, and Finish.
- Persist completion/skip through the profile API; handle save failure honestly.
- Return to the pending internal destination after completion or skip.
- Add tests for first-time display, persistence, keyboard flow, and failed save.
- Extend and integrate; do not rewrite working code.

Output:
- Onboarding components/state/API integration and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S11 — Your Contributions [frontend]

```text
You are implementing frontend step F-S11 for Project Amanah.

Mandatory first action:
- Read spec.md contributions and ownership requirements.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/security.md, and rules/testing.md.

Context:
- Authenticated routing and onboarding exist.
- No contribution mutations are implemented yet.

Task:
- Build the authenticated contributions list and detail surfaces against the typed API.

Requirements:
- Support typed variants for URL submissions, classification disputes, and prepared platform reports.
- Show title/URL, type, created/updated times, status, last public-safe event, and destination.
- Add cursor pagination if returned by the API.
- Handle empty, loading, unauthorized, and partial states without exposing another user’s data.
- Add component and provider-integration tests using deterministic fixtures.
- Extend and integrate; do not rewrite working code.

Output:
- Contribution types/hooks/pages/components and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S12 — URL submission [frontend]

```text
You are implementing frontend step F-S12 for Project Amanah.

Mandatory first action:
- Read spec.md URL submission and error requirements.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/security.md, and rules/testing.md.

Context:
- Contributions can be viewed and auth gating works.

Task:
- Add the single-public-URL submission flow and connect it to contributions.

Requirements:
- Provide visible label/help, client-side URL UX validation, submit state, and idempotency key.
- The backend remains authoritative for safety and support.
- On success show Processing and link to the new contribution.
- Handle duplicate, unsupported, inaccessible, rate-limited, expired-session, and retryable failures distinctly.
- Preserve user input across auth expiry or retryable failure without logging the URL.
- Add form and mutation tests.
- Extend and integrate; do not rewrite working code.

Output:
- Submission form/hook/status handling/tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S13 — Classification disputes [frontend]

```text
You are implementing frontend step F-S13 for Project Amanah.

Mandatory first action:
- Read spec.md classification-dispute flow and inspect F-S8–F-S12.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/security.md, and rules/testing.md.

Context:
- Item detail, authentication, and contribution history work.

Task:
- Implement “This is not hateful” as an authenticated, retry-safe dispute flow.

Requirements:
- Allow optional bounded context, explain manual review, and require explicit submission.
- Use idempotency; handle an existing open dispute by linking to it.
- Never change the displayed model prediction optimistically as though review completed.
- On success show Pending review and add/link the contribution.
- Show final disposition from the contribution detail when available.
- Add tests for anonymous gating, success, duplicate, retry, and status transitions.
- Extend and integrate; do not rewrite working code.

Output:
- Dispute form/dialog/hook/status integration and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S14 — Assisted platform reporting [frontend]

```text
You are implementing frontend step F-S14 for Project Amanah.

Mandatory first action:
- Read spec.md assisted-reporting flow and anti-brigading safeguards.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/security.md, and rules/testing.md.

Context:
- Auth, item detail, and contributions work.
- The backend supplies versioned candidate policies and persists prepared reports.

Task:
- Build the assisted platform-report preparation and outcome-tracking flow.

Requirements:
- Present candidate matches as uncertain; show official policy link/version/review date.
- Require the user to select or confirm a policy before saving.
- Show evidence summary and suggested wording with copy controls and an official report link/instructions.
- Never claim submission occurred and never automate the external report.
- Save a prepared record; later allow Submitted and platform outcome updates.
- Include anti-brigading and no-duplicate-mass-report guidance.
- Add tests for auth, policy selection, save, external-link safety, and outcome updates.
- Extend and integrate; do not rewrite working code.

Output:
- Reporting wizard/components/hooks/contribution integration and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S15 — Resources and coming-soon surfaces [frontend]

```text
You are implementing frontend step F-S15 for Project Amanah.

Mandatory first action:
- Read spec.md resource governance and coming-soon requirements.
- Read rules/general.md, rules/frontend.md, rules/testing.md, and rules/security.md.

Context:
- Public shell and item detail are complete.

Task:
- Implement the public resource catalog and honest nonfunctional community placeholders.

Requirements:
- Render reviewed resource entries by category and country/scope with organization, summary, URL, and last-reviewed date.
- Provide usable filtering without implying endorsement.
- Treat external links safely and visibly.
- Implement /forum as Coming soon and retain Comments coming soon below item pages.
- Do not add forms, fake counts, fake users, or fabricated discussions.
- Add resource filtering, empty-state, and coming-soon tests.
- Extend and integrate; do not rewrite working code.

Output:
- Resource page/components and coming-soon surfaces/tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S16 — Research report preview and PDF [frontend]

```text
You are implementing frontend step F-S16 for Project Amanah.

Mandatory first action:
- Read spec.md report/PDF requirements and inspect dashboard filter state.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/security.md, rules/testing.md, and rules/documentation.md.

Context:
- Filters are URL-backed and authenticated actions work.

Task:
- Build the filtered research-report creation, preview, and print/save-as-PDF flow.

Requirements:
- Inherit active filters and show scope, dates, sources, coverage, denominators, selected findings, citations, methodology, model disclosure, and limitations.
- Save the backend snapshot before presenting it as final.
- Redact harmful content and identifiers by default.
- Add a print stylesheet with accessible headings and no navigation/action chrome.
- If snapshot/PDF preparation fails, keep a usable preview and truthful retry state.
- Test filter inheritance, required disclosures, authorization, and print-specific rendering.
- Extend and integrate; do not rewrite working code.

Output:
- Report builder/preview/hooks/print CSS/tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S17 — Social-sharing mock [frontend]

```text
You are implementing frontend step F-S17 for Project Amanah.

Mandatory first action:
- Read spec.md mock-scope requirements.
- Read rules/general.md, rules/frontend.md, rules/testing.md, and rules/security.md.

Context:
- Reports, headlines, metrics, and item detail exist.
- Social publishing is intentionally not implemented.

Task:
- Add a coherent, clearly labelled demonstration of future social sharing.

Requirements:
- Provide entry points from approved report/news/stat surfaces only.
- Label the dialog/control Demo or Coming soon before any apparent completion.
- Do not request social credentials, call external APIs, open compose URLs with sensitive content, or emit analytics implying a share occurred.
- Include a safe local preview if useful and a close action.
- Add tests proving no external side effect and verifying mock labelling.
- Extend and integrate; do not rewrite working code.

Output:
- Mock sharing UI and tests.
- A short summary and verification.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S18 — Complete state and recovery coverage [frontend]

```text
You are implementing frontend step F-S18 for Project Amanah.

Mandatory first action:
- Read spec.md error/resilience requirements and inspect every P0 route.
- Read rules/general.md, rules/frontend.md, rules/api.md, rules/security.md, and rules/testing.md.

Context:
- P0 feature paths are implemented.

Task:
- Make loading, empty, partial, stale, fixture, offline, unauthorized, rate-limited, and retryable-failure behavior consistent and actionable.

Requirements:
- Reuse state primitives only where at least three real consumers justify them.
- Add an application error boundary for unexpected render errors; keep expected server errors in normal typed flow.
- Never silently replace live data with fixtures.
- Preserve safe user input across retryable mutation failures and auth expiry.
- Ensure every error message is actionable and excludes internal/provider details.
- Add route-level tests for each state and recovery action.
- Extend and integrate; do not rewrite working code.

Output:
- State primitives/integration/error boundary/tests.
- A short summary and verification matrix.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S19 — Accessibility, responsive, and print QA [frontend]

```text
You are implementing frontend step F-S19 for Project Amanah.

Mandatory first action:
- Read spec.md accessibility/UX requirements.
- Read rules/general.md, rules/frontend.md, rules/testing.md, and rules/security.md.

Context:
- All P0 routes and state handling exist.

Task:
- Audit and correct accessibility, responsive behavior, reduced motion, content safety, and print output.

Requirements:
- Complete keyboard-only flows, visible focus, modal focus trap/return, form labels, semantic headings, accessible names, and non-color status cues.
- Add chart text summaries or equivalent accessible data views.
- Verify 375, 768, 1024, and 1440 px layouts without clipped controls/charts.
- Respect reduced motion and high contrast.
- Verify print report hierarchy, page breaks, source URLs/citations, and hidden interactive chrome.
- Add automated accessibility checks plus focused regression tests; document required manual checks.
- Extend and integrate; do not rewrite working code.

Output:
- Accessibility/responsive/print corrections and tests.
- A short audit summary with any remaining manual risks.

If something is ambiguous, ask clarifying questions before producing code.
```

### Step F-S20 — End-to-end demo coverage and freeze [frontend]

```text
You are implementing frontend step F-S20 for Project Amanah.

Mandatory first action:
- Read spec.md success measures, demo script, and definition of done.
- Read rules/general.md, rules/frontend.md, rules/testing.md, rules/security.md, rules/devops.md, and rules/documentation.md.

Context:
- F-S1–F-S19 are complete.
- The frontend must now be stable against deterministic fixtures and the current live API contract.

Task:
- Add the minimal end-to-end suite and frontend runbook needed to freeze the hackathon demo.

Requirements:
- Cover homepage→dashboard→filter→item; anonymous action→auth→onboarding→return; URL contribution; dispute; prepared report; and research report print path.
- Run deterministic fixtures in CI and a separate smoke mode against the deployed API.
- Assert fixture/live/stale labels and prevent tests from calling production providers.
- Fix only defects revealed by the acceptance path; do not add scope.
- Document exact demo startup, fixture fallback, and known limitations.
- Run lint, typecheck, unit/component tests, accessibility checks, build, and E2E suite.
- Extend and integrate; do not rewrite working code.

Output:
- E2E tests, scripts/config, focused fixes, and demo documentation.
- A short final verification report.

If something is ambiguous, ask clarifying questions before producing code.
```
