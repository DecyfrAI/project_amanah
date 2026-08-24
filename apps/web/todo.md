# Outstanding work

Status of the frontend. Scope lives in `docs/frontend-todo.md`.
This file is what is actually left, not the unchecked arrival checklist.

New work cites **F-S** identifiers. Demo scope and its remaining work live in
`docs/completion-guide.md`.

## Done (24 August 2026)

- [x] **F-S9** Supabase Auth. `SessionProvider` restores the session before any
      protected route renders, in `live` and `demo` modes; `fixture` and
      `fallback` keep the tab-scoped rehearsal session.
- [x] **F-S21.1** Bearer token on every `live-provider.ts` request. `401` clears
      the stored session so the guard returns to login; `403` keeps the session
      and reports a denial.
- [x] **F-S21.2–.5** `live-provider.ts` reconciled with the shipped backend:
      `/v1/dashboard`, backend parameter names and snake_case shapes for
      `/v1/items` and `/v1/filters`, cursor pagination, and the nullable
      `published_at`/`scope` deltas on `/v1/news` (G5). Wire schemas mirroring
      the Pydantic contracts live in `src/api/wire.ts`.
- [x] **F-S21.6** Bundle split. Vendor chunks (react, query, zod, supabase) put
      the entry chunk at ~252 kB, under Vite's 500 kB warning.
- [x] **F-S21.7** Assisted reporting. `PolicyReportFlow` reads
      `POST /v1/items/{id}/policy-analysis`, requires explicit policy-version
      confirmation, saves through `POST /v1/prepared-reports`, and records
      outcomes through `PATCH /v1/prepared-reports/{id}`.
- [x] **F-S16** Research reports. `ResearchReportPanel` creates a real snapshot,
      renders its stored scope/coverage/figures/citations/limitations, downloads
      the aggregate CSV, and has print styles for Save as PDF.
- [x] Demo provider. `VITE_DATA_MODE=demo` routes product data to the live
      service with no catch-and-fallback; remaining mocks are labelled in place.
- [x] **PA-01** Persisted media-display preference, images visible by default,
      per-image Show/Hide. ADR 0010 amends ADR 0007; `spec.md` §18 updated.
- [x] **PA-02** Unscoped Image Evidence section removed from the Insights list,
      with its hook and component deleted.
- [x] **PA-03** Fixed nine-second entry hold removed; navigation follows the real
      auth/request lifecycle, with a bounded 60 s request timeout.
- [x] **PA-04** `View all insights` on every insight detail page, a success
      notice after creation, and duplicate-click protection on create.
- [x] **PA-06** Root `README.md` written for a reviewer.
- [x] `netlify.toml` already exists at the repository root; reviewed, not stale.

## Done (24 August 2026, second pass)

- [x] **F-S8** Item detail at `/app/explorer/:itemId`: model disclosure with the
      score, model/prompt/taxonomy versions, inference time, and rationale, the
      sampling limitation beside it, dataset provenance for datapack rows, the
      PA-01 media preference on any attached image, and a route to prepare a
      report. No author or person-level field anywhere.
- [x] **F-S11** Contributions history at `/app/contributions`, reading the
      owner-scoped `GET /v1/me/contributions`. Completes the reporting loop:
      a report saved in Reports now appears somewhere.

## Next

- [ ] **F-S3.4** 404 route and a standalone methodology page if marketing should
      still deep-link to one.
- [ ] **F-S12/F-S13** URL submission and dispute forms. Both backends exist
      (`POST /v1/submissions`, `POST /v1/items/{id}/disputes`) and both would
      surface in the Contributions history that now exists.
- [ ] **E2E coverage.** Nothing exists today — no Playwright, no `e2e/`
      directory — while `AGENTS.md` documents a `pnpm … e2e` command. Either add
      a small deterministic fixture-mode suite or correct that command.

## Descoped

- **PA-05 attachments — not part of the hackathon demo** (product-owner
  decision, 24 August 2026). Text notes work on viewer and machine-generated
  insights and the composer respects the server's `can_participate`; uploaded
  attachments were excluded deliberately, for safety rather than time. Arbitrary
  uploads into a shared thread would need malware scanning, safe download
  handling, per-attachment authorization, and an ADR superseding ADR 0004, which
  refused a screenshot board because it would redistribute the material this
  product exists to measure. Rationale is recorded in `docs/completion-guide.md`.
  Do not add attachment controls without reopening that decision.

## Later

- [ ] F-S17: the declared sharing mock.
- [ ] F-S18 to F-S20: resilience inventory, accessibility QA, E2E demo freeze.

## Do not do

- Person-level search, ranking, or repeat-offender views.
- Auto-send platform reports.
- Call YouTube, Reddit, Gemini, or any secret-backed provider from the browser.
- Treat fixture figures as live readings.
- Redistribute `public/media/fixtures/memes/`.
