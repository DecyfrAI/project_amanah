# Outstanding work

Status of the frontend. Scope lives in `docs/frontend-todo.md`.
This file is what is actually left, not the unchecked arrival checklist.

New work cites **F-S** identifiers.

## Next

- [ ] **F-S9** Wire Supabase Auth. Replace the fixture `sessionStorage` session.
      `@supabase/supabase-js` is already a production dependency and unused.
- [ ] **F-S21.1** With F-S9: attach the Supabase access token to every
      `live-provider.ts` request (there is no Authorization header today, so
      every live `/v1` call 401s) and treat 401 as expired-session.
- [ ] **F-S21.2–.5** Reconcile `live-provider.ts` with the shipped backend:
      `/v1/overview` → `/v1/dashboard`, backend param names and snake_case
      shapes for `/v1/items` and `/v1/filters`, cursor pagination. The gap
      list is `docs/frontend-backend-reconciliation.md` (G1–G11). News stays
      as-is; the backend aligns `/v1/news` in B-S9.
- [ ] **F-S8** Item detail route with redaction, reveal, and gated actions.
- [ ] **F-S3.4** 404 route and a standalone methodology page if marketing should
      still deep-link to one.
- [ ] **F-S21.6** Split the ~535 kB main bundle under Vite's 500 kB warning
      before the demo.
- [ ] Add `netlify.toml` (npm, not pnpm) when a preview host is chosen.

## Later

- [ ] F-S11 to F-S14: contributions, URL submit, disputes, assisted reporting
      that actually persist through the API.
- [ ] F-S16 / F-S17: research-report PDF and the declared sharing mock.
- [ ] F-S18 to F-S20: resilience inventory, accessibility QA, E2E demo freeze.
- [ ] Remove unused `@supabase/supabase-js` if F-S9 is deferred past the demo.

## Do not do

- Person-level search, ranking, or repeat-offender views.
- Auto-send platform reports.
- Call YouTube, Reddit, Gemini, or any secret-backed provider from the browser.
- Treat fixture figures as live readings.
- Redistribute `public/media/fixtures/memes/`.
