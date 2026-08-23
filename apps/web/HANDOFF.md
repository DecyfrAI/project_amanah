# Handoff

State of the frontend, and what to pick up next.

**Read `AGENTS.md` first.** It and `rules/` are the contract. Product source of
truth is `docs/spec.md`. Outstanding work is `todo.md`. New work
cites **F-S** step identifiers.

Run `npm run verify` from `apps/web/` before every commit.

---

## Reading the plans

Two things about the planning documents will mislead you otherwise.

**The checklists describe scope, not progress.** `docs/frontend-todo.md` arrived
with every box unchecked, which does not describe this repository: F-S1 through
F-S3 and much of F-S5 are built and tested. Read it as the list of what is in
scope. The build state lives in git, in the ADRs, and in the Done section below.

**Two step-numbering schemes are in the tree.** The v1 plan
(`docs/planning/PROJECT_AMANAH_FRONTEND_DEVELOPMENT_PLAN.md`) uses FE-01 to
FE-14; the current plan uses F-S1 to F-S20, and both appear in code comments.
New work cites **F-S**. Leave existing FE- references alone: a stale comment is
less confusing than an edit that touches every file for no behavioural reason.

---

## Done

### Foundation

- Vite 8, React 19, TypeScript 6 with `strict`, `noUncheckedIndexedAccess` and
  `exactOptionalPropertyTypes`. Production dependencies pinned exact.
- oxlint, Prettier, Vitest + Testing Library. See `docs/adr/0003`.
- Design tokens in `src/styles/tokens.css`. Contrast pairs are asserted in
  `tokens.contrast.test.ts`.
- `ErrorBoundary` and `PageSkeleton`. Route-level `lazy()` + `Suspense`.

### API and fixtures

- Zod contracts in `src/api/contracts.ts`, one `apiClient` interface, fixture
  and live providers selected by `VITE_DATA_MODE`.
- Synthetic/redacted fixtures in `src/fixtures/`. Numbers are derived so
  Overview, Explorer, and Insights stay consistent.
- `FixtureBanner` is visible in `fixture` and `fallback` modes.

### Auth and shell

- Public marketing, `/login`, `/signup`, and `/resources`.
- `/app/*` sits behind a fixture session (`sessionStorage`). Supabase Auth is
  not wired yet. `@supabase/supabase-js` is listed for that step and is unused.
- App shell, workspace nav, theme toggle, first-run tour, Ask Amanah.

### Product surfaces

| Route                           | What is real                                            | What is still a declared mock          |
| ------------------------------- | ------------------------------------------------------- | -------------------------------------- |
| `/`                             | Marketing argument, including the Path section          |                                        |
| `/resources`                    | Lesson modules and activities                           |                                        |
| `/app`                          | Overview: coverage, KPIs, rate/volume, breakdowns, news |                                        |
| `/app/explorer`                 | Filtered records, redaction, image reveal               | No item-detail route yet               |
| `/app/insights`                 | Snapshots and discussion                                |                                        |
| `/app/review`                   | Queue UI                                                | Queue rows are illustrations           |
| `/app/reports`                  | Draft prep, image catalog, evidence classify            | Connectors are not live                |
| `/app/connections`              | Connector list UI                                       | Run times and counts are illustrations |
| `/app/settings`, `/app/profile` | Local fixture session only                              |                                        |

Marketing leads to Log in and Sign up, and there is no anonymous `/dashboard`.
That is `docs/spec.md` (FR-HOME-005, FR-HOME-006, FR-DASH-008) and ADR 0001,
which supersedes ADR 0006. The `PublicDashboardPage` that rendered the dashboard
without a session was removed on 23 August 2026; `DashboardView` now has one
caller, inside `AuthGuard`.

### Media

- Hero clip, stage photographs, path stills, generated case stills, and the
  research image corpus under `public/media/fixtures/memes/` (ADR 0007).
- Brand assets come from `scripts/build_brand_assets.py`. Do not hand-crop.

---

## Not started, or only stubbed

- **F-S9:** Supabase session. Login currently writes a fixture session.
- **F-S8:** Item detail route (`/items/:id` in the spec, behind the session).
- Standalone `/methodology` and `/presentation` routes from the v1 plan.
- A 404 route (F-S3.4).
- `netlify.toml`. Must use npm, not pnpm.
- Live FastAPI: `live-provider.ts` exists; it needs a reachable service.

---

## Constraints that are not negotiable

- Every rate shows its numerator, denominator, and collection coverage.
- Missing collection renders as a gap, never as zero.
- Relevance is separate from hate.
- Reviews append. A model prediction is never overwritten.
- Harmful content is blurred or collapsed by default.
- "Classified as **likely** anti-Muslim hate", never "is hate", until reviewed.
- "Coincides with", never "caused by".
- No person-level features.
- Nothing sensitive behind a `VITE_` variable.
- No em dashes anywhere except quoted material.
- WCAG 2.2 AA.

---

## Needs a human

1. **Verify the Qur'anic translations** in `AmanahSection.tsx` against a printed
   or publisher copy before any demo. Each reference links to quran.com.
2. **Keep the GitHub repository private.** The research image corpus is not for
   redistribution.
3. **Supply Supabase credentials** when F-S9 starts: `VITE_SUPABASE_URL` and
   `VITE_SUPABASE_ANON_KEY`. Both are public by design.
4. **Confirm the API contract with the backend contributor** before the live
   provider is pointed at a real service.
