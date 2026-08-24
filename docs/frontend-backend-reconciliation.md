# Frontend ↔ backend reconciliation

Date: 23 August 2026. Gap status updated 24 August 2026.

## Gap status, 24 August 2026

| Gap | Status |
|---|---|
| G1 Authorization header | **Closed.** Every `live-provider.ts` request carries the Supabase access token; `401` clears the session, `403` does not. |
| G2 `/v1/overview` → `/v1/dashboard` | **Closed.** The frontend calls `/v1/dashboard` and maps `DashboardResponse` into the Overview view model. Per-source daily stacks and composition breakdowns are not computed live, so they render as an honest absence rather than an invented split. |
| G3 `/v1/items` shape and parameters | **Closed.** Backend parameter names, snake_case item shape, and cursor pagination adopted. `matched` is nullable because keyset pagination returns no total, and the UI no longer promises one. `hate_types` and `q` have no server filter, so they are not sent and the `applied` echo reports the scope actually requested. |
| G4 `/v1/filters` shape | **Closed.** The backend response is adopted. `available` is null (the service reports no available-data window), so the date picker bounds the *query* and says so instead of claiming data exists. |
| G5 `/v1/news` contract | **Closed.** Nullable `published_at` and `scope` absorbed; an absent publication time renders as "Publication time not stated", never the retrieval time. |
| G6 Insights, discussion, captures | **Closed.** All routes wired; the composer respects the server's `can_participate` (ADR 0004 invite-only). |
| G7 Grounded assistant | **Closed.** `POST /v1/assistant/query` wired with filters, citations, limitations, and `grounded_in`. |
| G8 Image catalogue and classification | **Partly closed.** The catalogue and classification of a catalogued image are wired. **Upload of a user's own file has no backend route** (`B-S28`); the live path refuses visibly. |
| G9 Assisted-report flow | **Closed.** `PolicyReportFlow` implements the policy-catalogue path with explicit version confirmation and the allow-listed email-draft split. |
| G10 `PATCH /v1/me` | **Closed.** Used by the PA-01 media preference. |
| G11 Public `/resources` | **Closed** by decision; no code change. |

Carried-over flags still open: the repository must stay private, line-ending
renormalisation, and the Qur'anic translation check below.
Inputs: shipped frontend (`apps/web`, see `apps/web/HANDOFF.md`), backend through
Milestone 2 (`backend/`), `spec.md` §13, `docs/news-rss-sources.md`, and the
product owner's change requests of 23 August 2026.

This document records every gap that would stop the shipped frontend from
working against the planned backend, the agreed direction for each, and where
the work now lives in `backend-todo.md` / `frontend-todo.md`. Per `AGENTS.md`,
backend OpenAPI/Pydantic contracts are the service-boundary source of truth;
the frontend conforms to them, and genuinely new surfaces get backend plan
steps (and, before implementation, an additive `spec.md` §13 amendment).

## 1. Blocking gaps

### G1 — No Authorization header on any live request (blocking)

`apps/web/src/api/live-provider.ts` (`requestJson`) sends no bearer token.
Every `/v1` product endpoint requires server-verified Supabase JWT auth, so
every live call will 401. The session itself is still a fixture
(`sessionStorage`); F-S9 wires Supabase Auth.

**Direction:** part of F-S9. Attach the Supabase access token to every live
request, handle 401 as expired-session (refresh or re-login), and never store
the token outside the Supabase client's own persistence.

### G2 — `GET /v1/overview` does not exist (blocking)

The frontend calls `/v1/overview` expecting the camelCase `OverviewSchema`
(coverage with `containersMonitored`, metric cards, daily series with
per-source stacks, breakdowns). The spec and shipped backend expose
`GET /v1/dashboard` returning snake_case `DashboardResponse` (coverage,
metrics, trend, headlines, sampling disclosure, meta).

**Direction:** the frontend adopts `/v1/dashboard` and its shape (spec §13.2
is authoritative; the backend shipped it in Milestone 2). Gaps in the backend
response that Overview genuinely renders (per-source daily stacks,
breakdowns by hate type/platform/severity/review state) are **additive**
backend work: extend `DashboardResponse` additively in a follow-up step, or
frontend derives breakdowns from `/v1/items` where volumes allow. Do not keep
a parallel `/v1/overview`.

### G3 — `/v1/items` shape and query-parameter mismatch (blocking)

- Frontend sends `from`, `to`, `platform`, `hate_type`, `severity`,
  `review_state`, `q`; backend validates `date_from`, `date_to`, `platforms`,
  `severities`, `review_states`, `content_kinds`, `country_codes`,
  `narrative_tags`, `confidence_tiers`, `dataset_*`, `sort`, `cursor`,
  `limit`. Unknown params are rejected, so every filtered request fails.
- Backend has **no `hate_type` filter and no free-text `q`** on `/v1/items`.
- Frontend expects `ExplorerPageSchema` (`applied`, `matched`, `returned`,
  camelCase items, no cursor); backend returns `CursorPage[ItemSummary]`
  (snake_case, `page.next_cursor`, no total match count).

**Direction:** frontend adopts the backend parameter names, snake_case item
shape, and cursor pagination. Two additive backend items: a `hate_types`
filter on `/v1/items` (the enum already exists on `ItemSummary`) and a
decision on `q` (either a bounded server-side text search or the frontend
drops/keeps it client-side against the fetched page only — do not silently
pretend it searched the corpus). `matched` totals: keyset pagination does not
return totals; the frontend UI must not promise one.

### G4 — `/v1/filters` shape mismatch (blocking)

Frontend `FilterOptionsSchema` (available window, `defaultWindowDays`,
options as `{value,label,count}`) vs backend `FilterOptionsResponse`
(enum lists, datasets, sorts, `max_window_days`, `max_page_limit`).

**Direction:** frontend adopts the backend response. If the calendar needs an
available-data window and per-option counts, that is additive backend work —
record it as a follow-up on the dashboard/read API, not a frontend reshape.

### G5 — `/v1/news` contract conflict (blocking)

Backend Milestone 2 shipped `/v1/news` as `CursorPage[ItemSummary]` (news as
classified-item projections). The frontend and `docs/news-rss-sources.md`
(the B-S9 hand-off both sides reviewed) define a **context news stream**:
snake_case `NewsListSchema` with `window`, `applied`, `coverage`,
`data_mode`, `next_cursor`, `items` carrying publisher metadata only and
**no** hate label, score, or review state.

**Direction:** B-S9 implements the hand-off contract for `/v1/news`
(B-S9.7–B-S9.9 in `backend-todo.md`). The current items-shaped `/v1/news`
route has no consumer; rework it in B-S9 with OpenAPI and contract tests
updated together. Classified news *item cards* (F-S7.1/F-S8.2) remain a
different surface served by `/v1/items`.

**Status (backend, Milestone 3):** done. `/v1/news` now returns `window`,
`applied`, `coverage`, `data_mode`, `next_cursor`, and publisher-metadata items
with no hate label, score, severity, or review state; the projection behind it
has no column for one. Two deltas the frontend contract should absorb in F-S21:
`published_at` is nullable (a feed that states no publication date must not have
the retrieval time substituted for it), and `scope` is nullable (a stored
`geographic_scope` outside `local`/`global` is reported absent rather than
rounded to whichever looks closer). The response also carries the standard
`meta` envelope; `z.object` ignores it.

### G6 — Insights, discussion, captures, viewer posts: no backend (blocking for `/app/insights`)

The frontend ships `/app/insights` (snapshot insights, invite-only
discussion, reactions, retract, dashboard captures, profile note list) and
calls `GET/POST /v1/insights`, `GET /v1/insights/{id}`,
`GET /v1/insights/{id}/discussion`, `POST …/discussion/posts`,
`POST /v1/posts/{id}/reactions`, `POST /v1/posts/{id}/retract`,
`POST /v1/captures`, `GET /v1/me/posts`. None are in spec §13 or the backend
plan. ADR 0004 records the product decision; the Milestone 2 schema already
has an `insight_snapshots` table to build on.

**Direction:** new backend step **B-S27** (Milestone 5). The additive spec
§13 amendment landed in spec v2.2 (23 Aug 2026). Constraints from ADR 0004
bind:
attached to insights, invite-only, no author ranking, retraction leaves the
row, captures are first-party figure captures only.

### G7 — Grounded assistant (`Ask Amanah`): no backend (degrades, not blocking)

Frontend calls `POST /v1/assistant/query` (`AssistantAskInputSchema` →
`AssistantReplySchema` with citations, limitations, `groundedIn`). Not in
spec §13 or the backend plan. Default starter queries already exist in
`apps/web/src/features/ask/ask-prompts.ts` (rate, trend, coverage, an
explorer entry, current events, news-coincides-with-rate) — the product
owner's "default queries" request is already satisfied on the frontend.

**Direction:** new backend step **B-S25** (Milestone 4, after B-S15): answer
only from stored fact bundles and methodology text, cite every number,
refuse causal claims ("coincides", never "caused"), typed
insufficient-data/unavailable results. The spec §13 amendment landed in
spec v2.2.

### G8 — Image evidence catalog and classification: no backend (501 stubs)

`listImageExamples` and `classifyEvidence` throw 501 in the live provider by
design. ADR 0007 defines the boundary: pixels never cross `src/api/`; object
storage holds bytes; Postgres holds path/sha256/mime/size/annotation/
prediction; API returns short-lived signed URLs plus the classification.

**Direction:** new backend step **B-S26** (Milestone 4). Routes
`GET /v1/image-examples` and `POST /v1/image-classifications` landed in the
spec v2.2 §13 amendment. See §2.6 below for the ingestion half of the
product owner's image request.

### G9 — Assisted-report draft flow diverges from spec §9.9 (RESOLVED 23 Aug 2026)

Frontend `ReportDraftSchema` is an email-style draft (platform guess,
`to`/`subject`/`body`, allow-listed address). Spec §9.9 / B-S18 define a
policy-catalog flow: candidate policy matches with versions and official
links, explicit user confirmation of the policy, prepared-report record.

**Decision (product owner):** hybrid. Platforms with an official reporting
form use the policy-catalog flow; a platform without one gets the
email-style draft addressed only to a reviewer-approved allow-listed
address, never auto-sent. Recorded as FR-TOS-010 (spec v2.2) and B-S18.9;
the frontend contract already models this split (`to_kind:
placeholder|allowlist`, nullable `official_report_url`). The draft screen
remains a declared mock until B-S18 lands (F-S21.7).

### G10 — `PATCH /v1/me` not implemented

Spec §13.2 lists `GET/PATCH /v1/me`; Milestone 2 shipped GET only. Frontend
onboarding (F-S10.4) persists completion through the profile API.

**Direction:** added to B-S27 as its first sub-item (small, unblockable
earlier if F-S10 needs it sooner).

### G11 — Public `/resources` route (RESOLVED 23 Aug 2026)

The shipped frontend serves lesson/education content anonymously at
`/resources` (marketing-framed `LessonsPage`). Spec v2.1 and `AGENTS.md`
placed Resources behind authentication; backend `/v1/resources` denies
anonymous access (correctly). The public pages are static editorial content
and call no product API, so nothing leaks.

**Decision (product owner):** serve anonymously. The static lesson library
is a public marketing surface with a binding no-product-API constraint;
the reviewed catalog behind `/v1/resources` stays authenticated. Recorded
in ADR 0008 and spec v2.2 §7.1/§7.2. No code change; FE-GATE-SEC-09 tests
extend to the lesson pages.

## 2. Product-owner change requests (23 August 2026) — disposition

| # | Request | Disposition |
|---|---|---|
| 1 | Filter news feeds to what's relevant | **B-S9.7**: apply the per-feed topical filters from `docs/news-rss-sources.md` (keep religion/hate-crime/public-affairs/mosque/court/election coverage; drop sport/celebrity), config-driven per feed, allowlist only. Neutral reporting stays in scope; Muslim-related vocabulary is never itself a harm signal. |
| 2 | Check posts against DB and dedupe before insertion | Already planned: B-S9.4 (canonical URL + provider/headline), B-S12.5–B-S12.8 (content hashes, canonical keys, idempotent upserts, datapack row identity). B-S9.4 wording now says explicitly: dedupe checks run against the database before insert, and a duplicate links to the existing row. |
| 3 | Do not remove profanity — researchers need the original wording | **B-S12.9** (new): stored original and normalized text is never masked, censored, or profanity-filtered; redaction/blurring is a display-layer concern (F-S7.5, FE-GATE-SEC-06) and report-snapshot redaction (B-S20.3) only. |
| 4 | RSS feeds list | Already in-repo verbatim as `docs/news-rss-sources.md`; B-S9 now cites it as the required allowlist. Do not add feeds it rejected; do not invent replacements. |
| 5 | Chat agent with default queries (posts, entries, trends, current events, correlations) | Frontend already ships the starter chips (`ask-prompts.ts`). Backend: **B-S25**. "Correlations" are surfaced as *coincidence* with citations — the assistant must refuse causal phrasing (spec §3.3). |
| 6 | Pull and classify images (Reddit/YouTube), image + metadata instead of comment | **B-S26** classifies image evidence behind the API (ADR 0007 boundary). Live *ingestion* of images is gated by spec §10.2: Reddit is disabled/fixture-only until Reddit-for-Researchers approval and credentials exist, and YouTube comments cannot carry images (thumbnails/video frames would be a separate reviewed decision). Until then the corpus is the reviewed research datapack plus user-submitted URLs. Revisit when Reddit approval lands. |
| 7 | New insights generated on each data pull | Already planned: the ETL chain ends `… aggregate → insights → finalize` (B-S21.2) and B-S15.7 caches by filter/data/model/prompt version, so new data invalidates and regenerates. **B-S15.10** makes the per-run refresh explicit. |
| 8 | Backfill ~5 years of historical data | **B-S24** (new, Milestone 3): bounded historical backfill through the same canonical pipeline — reviewed datapacks as the primary historical source, GDELT/RSS historical windows for news where terms permit, YouTube official-API seed queries with explicit date windows. Strata and provenance rules apply unchanged; no scraping; backfilled buckets carry their own coverage so old sparse windows render as gaps, not zeros. |

## 3. Flags carried over from the frontend hand-off

- **Repository must stay private.** `apps/web/public/media/fixtures/memes/`
  is a sourced research image corpus marked
  `internal-research-fixture-not-for-redistribution` (ADR 0007). It must be
  removed before the repo could ever be made public. B-S23.4's
  forbidden-file scan should assert the pack never lands in a build artifact
  or public bucket.
- **Main JS bundle is ~535 kB**, tripping Vite's 500 kB warning. Split
  before the demo (route-level chunks are already lazy; look at chart and
  Zod-heavy chunks). Tracked in `frontend-todo.md` (F-S21.6).
- **Line endings**: `.gitattributes` is in place but existing files need one
  coordinated renormalization commit, agreed by both contributors, to stop
  whitespace-noise diffs.
- **Verify the Qur'anic translations** in `AmanahSection.tsx` against a
  printed or publisher copy before any demo (human task; product owner
  deferred on 23 Aug 2026 — still open, must close before a demo).
- **Supabase credentials** (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`)
  are needed when F-S9 starts (deferred 23 Aug 2026; F-S9/F-S21.1 are
  blocked until they arrive).

## 4. Sequencing note

The demo-critical path is: F-S9 (auth + bearer header) → frontend contract
reconciliation (F-S21) against the shipped Milestone 2 API → B-S9 news
(unblocks the Overview news stream live) → B-S15/B-S25 (assistant) →
B-S26/B-S27 (images, insights) → B-S24 (backfill, any time after Milestone 3
adapters exist). All decisions are now resolved: G9 (hybrid report flow,
FR-TOS-010), G11 (anonymous lesson library, ADR 0008), and the spec §13
amendment for G6/G7/G8 (spec v2.2, 23 Aug 2026). Nothing in this document
blocks on a pending decision; F-S9/F-S21.1 wait only on Supabase
credentials.
