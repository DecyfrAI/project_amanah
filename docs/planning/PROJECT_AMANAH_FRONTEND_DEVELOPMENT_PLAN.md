# Project Amanah — Frontend Development Plan

**Version:** 1.1 — 48-hour hackathon edition  
**Brand:** Project Amanah — Monitoring Anti-Muslim Hate Online  
**Frontend:** React, Vite and TypeScript on Netlify  
**Backend relationship:** API developed in parallel by another contributor; frontend is mock-first and contract-driven

> **Open-datapack addendum (2026-08-22):** Datapack item cards and filters display source/platform as `N/A` and expose Dataset provider/name/version separately when public-safe. Item detail preserves dataset/license provenance. See the authoritative root [`spec.md`](../spec.md).

> **Authentication-scope addendum (2026-08-22):** Only the marketing homepage and authentication entry/callback routes are anonymous. Restore the session before resolving routes, deny every application route by default, and do not issue protected API requests from the marketing page or before session validation. The root [`spec.md`](../spec.md) is authoritative.

## 1. Frontend outcome

Ship one coherent experience:

```text
Marketing page
 → Log in
 → Overview dashboard
 → Click a trend/spike
 → Explorer opens with matching filters
 → Inspect a redacted supporting record
 → Record a human review decision
 → Preview a filter-scoped report
```

Also ship a public or unlisted browser-based presentation route for recording the YouTube demonstration.

The frontend should make Project Amanah’s meaning and usefulness immediately understandable. *Amanah* is a trust: we are entrusted with one another’s wellbeing and should not become indifferent to harm. The product turns isolated, exhausting incidents into scoped patterns, contextual evidence, human-reviewed findings and responsible reports. Its visual and interaction design must embody trustworthiness—justice, care, accuracy, restraint and accountability—and must never look like a surveillance, policing or automated-takedown product.

## 2. Scope and priority

### P0 — must work

- Final logo/wordmark and basic brand tokens
- Public marketing page
- Login/logout and protected application shell
- Overview with coverage, KPIs, trend, narratives and signal cards
- Explorer with search, filters, table, item drawer and chart drill-down
- One append-only human review interaction
- Loading, empty, error and fixture states
- Responsive layout and keyboard accessibility
- Netlify deployment

### P1 — ship after P0 is stable

- Insights brief with citations and event/forecast caveats
- Print-optimized filtered report preview and aggregate CSV action
- Connections page showing honest live/access-required/fixture states
- Three prepared Meme Signals examples
- HTML presentation deck and accurate transcript/captions script

### P2 — cut first

- Interactive Ask Amanah chat
- Dedicated Narratives route instead of an Overview section
- Dedicated Meme Signals route instead of prepared cards
- Saved searches/views
- Advanced theme/settings controls
- Animated charts or elaborate transitions
- Community Discovery Queue UI beyond one fixture card

### Do not build for the hackathon

- Person-level “repeat offender” tracking
- Live X, Meta, TikTok or Reddit collection in browser code
- Raw or item-level bulk export
- Autonomous source/community activation
- Frontend calls directly to YouTube, Reddit, Gemini or other secret-backed providers

## 3. Parallel-work strategy

The frontend must not wait for the backend.

1. Freeze shared TypeScript response types from the agreed API examples.
2. Build a single `apiClient` interface.
3. Implement a fixture-backed provider immediately.
4. Build all screens against synthetic/redacted fixtures.
5. Swap the provider to the live FastAPI base URL without changing components.

Use one environment switch:

```dotenv
VITE_DATA_MODE=fixture
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

Allowed `VITE_DATA_MODE` values:

- `fixture`: all application data comes from committed synthetic/redacted JSON.
- `live`: authenticated requests go to FastAPI.
- `fallback`: try FastAPI, then show a visible “Fixture data” banner if the request fails.

Never silently substitute fixture data for live data.

## 4. Backend handoff contract

Agree on these before frontend hour 3:

- Base URL and health endpoint
- Supabase JWT format and authenticated request header
- UTC ISO timestamp format
- Cursor pagination shape
- Error envelope and stable safe error codes
- Controlled enums for source, content type, stance, severity and review state
- Whether missing values are `null`, absent or explicit `unavailable`
- CORS origins for local Vite and deployed Netlify URLs
- Fixture/live-data indicator

Minimum response contracts required by the frontend:

```text
GET  /healthz
GET  /v1/overview
GET  /v1/search
GET  /v1/search/suggestions
GET  /v1/items/{id}
POST /v1/reviews
GET  /v1/insights
GET  /v1/connections
POST /v1/reports
GET  /v1/reports/{id}
```

The backend contributor should provide OpenAPI JSON as soon as routes stabilize. Generate or reconcile TypeScript types once; do not maintain separate hand-written live and fixture models.

## 5. Recommended frontend structure

```text
apps/web/
├── public/
│   ├── brand/
│   │   ├── amanah-mark.svg
│   │   ├── amanah-wordmark.svg
│   │   ├── amanah-wordmark-inverse.svg
│   │   └── favicon.svg
│   └── presentation/
│       └── backup-images/
├── src/
│   ├── app/
│   │   ├── router.tsx
│   │   ├── providers.tsx
│   │   └── auth-guard.tsx
│   ├── api/
│   │   ├── client.ts
│   │   ├── contracts.ts
│   │   ├── fixture-provider.ts
│   │   └── live-provider.ts
│   ├── brand/
│   │   ├── Logo.tsx
│   │   └── tokens.css
│   ├── components/
│   │   ├── charts/
│   │   ├── content/
│   │   ├── filters/
│   │   ├── layout/
│   │   ├── reports/
│   │   └── ui/
│   ├── features/
│   │   ├── auth/
│   │   ├── overview/
│   │   ├── explorer/
│   │   ├── insights/
│   │   ├── memes/
│   │   ├── review/
│   │   ├── reports/
│   │   └── connections/
│   ├── fixtures/
│   │   ├── overview.json
│   │   ├── items.json
│   │   ├── insights.json
│   │   ├── report.json
│   │   └── connections.json
│   ├── pages/
│   │   ├── marketing/
│   │   ├── dashboard/
│   │   ├── methodology/
│   │   └── presentation/
│   ├── styles/
│   │   ├── global.css
│   │   ├── print.css
│   │   └── presentation.css
│   └── test/
├── netlify.toml
└── package.json
```

Keep fixture data visibly synthetic. Do not commit real hateful text, personal identifiers or unlicensed screenshots.

## 6. Routes

### Public

- `/` — marketing page
- `/login` — invited-account login
- `/methodology` — public-safe methodology and limitations
- `/presentation` — HTML slide deck for recording; unlinked from ordinary navigation if desired

### Protected

- `/app` — Overview
- `/app/explorer` — search, filters and supporting records
- `/app/insights` — grounded analysis and citations
- `/app/review` — human review queue/action
- `/app/reports` — report history/preview
- `/app/connections` — safe integration status
- `/app/settings` — content-safety preferences if time permits

Narratives and Meme Signals may be sections or drawers inside Overview/Insights for the MVP rather than separate routes.

## 7. Branding and logo workstream

### Direction

Use the existing brand system: institutional, humane and restrained. The symbol should combine an abstract open arch/shield with a subtle signal/ripple. Avoid police badges, targets, eyes, mosque silhouettes, generic crescent-and-star marks and decorative Arabic calligraphy.

### Fast design process

1. Sketch three monochrome concepts only.
2. Test each at favicon size and beside the full name.
3. Select one within 60–90 minutes; do not hold a prolonged logo process.
4. Build the final mark as clean SVG paths.
5. Produce horizontal, compact, inverse and mark-only variants.
6. Verify legibility on ivory, white and navy backgrounds.

### Required brand assets

- Primary horizontal wordmark
- Inverse wordmark
- Standalone mark/favicon
- SVG source and optimized export
- Social/YouTube presentation title lockup
- Color tokens and typography variables
- One-page usage sample showing safe/unsafe placement

### Acceptance criteria

- Recognizable at 24 px
- Works in one color
- Does not resemble a police/surveillance symbol
- Conveys protection and stewardship without aggression or triumphalism
- Tagline remains readable in presentation and marketing contexts
- Logo includes meaningful accessible text or adjacent brand name

## 8. Marketing site workstream

### Story flow

1. **Hero:** “A trust we carry together.” Then: “Understand how anti-Muslim hate moves online.”
2. **Meaning of Amanah:** we are entrusted with one another’s wellbeing; concern should lead to truthful, wise and just action.
3. **Human problem:** isolated incidents disappear into feeds; repeated exposure can create fatigue, numbness and normalization.
4. **Capability gap:** communities need longitudinal context, not another stream of harmful posts.
5. **Three questions:** How much in this monitored sample? What narratives are appearing? What changed around it?
6. **Workflow:** Capture → Classify → Contextualize → Human review → Learn and report. Present this as the trust made operational.
7. **Product proof:** animated only through subtle chart/filter transitions using synthetic data.
8. **Meme intelligence:** image + OCR + post context, with blurred examples.
9. **Community/news context:** approved community-level monitoring and local/global event association.
10. **Responsible use:** justice in classification, restraint in collection, no person profiling, no causal overclaim, no unapproved data transfer and clear coverage limitations.
11. **Methodology/disclosure:** tools, datasets, licenses, earlier work and human checks.
12. **Call to action:** “Carry the trust with care.” Then: Log in.

### Hero content

```text
Project Amanah
Monitoring Anti-Muslim Hate Online

A trust we carry together.

Understand how anti-Muslim hate moves online.

Turn authorized public signals into trends, narratives, context and
reviewable reports—without profiling people.
```

Primary action: `See how it works`  
Secondary action: `Log in`

### Meaning-of-Amanah copy

Use this short section immediately after the hero:

> Amanah is a trust. We are entrusted with the care of one another and called to stand for what is good and resist what causes harm. Project Amanah carries that responsibility into the digital public square: making anti-Muslim hate visible, contextual and reviewable so communities can respond with evidence, wisdom and justice—without surrendering anyone’s dignity.

If **ghayrah** (or *gheerah*) appears in narration or extended copy, define it once as disciplined protective concern for the deen and community—the refusal to normalize or become numb to harm. Pair it with truth, mercy, wisdom and justice. Never use it as shorthand for anger, possessiveness, vigilantism or policing individuals. Likewise, explain “enjoining good and forbidding wrong” as responsible witness, care and principled response—not coercion or automated punishment. Project Amanah is not a religious authority; seek scholar/community-advisor review before using the wording in a production campaign.

### Marketing components

- Public header and mobile menu
- Hero with restrained dashboard preview
- Meaning-of-Amanah section connecting the name to product behavior
- Problem/story section
- Three-question cards
- Workflow diagram
- Dashboard proof section
- Responsible-use callout
- Methodology/disclosure list
- Footer

### Acceptance criteria

- A visitor understands the problem, user and solution within 20 seconds.
- A visitor understands why the project is called Amanah and how that trust becomes fair, restrained, accountable product behavior.
- The page explains usefulness before describing ML.
- No real hateful content or identifiable person appears.
- Login is visible but not dominant over the mission.
- Mobile layout works at 375 px without clipped charts or typography.
- Reduced-motion mode removes nonessential movement.

## 9. Dashboard workstream

### Shared application shell

- Left navigation on desktop; compact drawer on mobile
- Project Amanah wordmark
- Global date, platform/source and community/channel filters
- Fixture/live-data banner
- User/profile menu
- Content-safety controls: blur media and redact harmful text
- Persistent filter state in URL query parameters

### Overview

Build in this order:

1. Coverage strip: monitored source/query/community, records, date window and last run.
2. KPI cards: observed, Muslim-related, likely anti-Muslim, likely-hate rate, reviewed/confirmed and change.
3. Daily likely-hate rate line chart with denominator and missing-data gaps.
4. Daily volume columns.
5. Narrative and severity horizontal bars.
6. Latest signals with event-association caveat.
7. Experimental forecast card only if a valid backend/fixture response exists.

Every chart point/bar gets:

- tooltip with numerator, denominator and exact date/filter scope;
- keyboard focus and accessible text;
- `View supporting records` action;
- navigation to `/app/explorer` with matching URL filters.

### Explorer

- Search field with safe autocomplete
- Filter chips and Reset
- Date, platform, community/channel, query, sampling stratum, narrative, severity, confidence and review-state filters
- Cursor-paginated table
- Redacted content preview
- Published/observed times
- Model and review badges
- Item detail drawer
- Source link only where permitted

The item drawer shows:

- Content warning and deliberate reveal control
- Focal text or blurred media
- Parent/root context
- Source/query/community and timestamps
- Model label, confidence, rationale and version
- Human review history
- Evidence/provenance identifiers

### Review

MVP actions:

- Confirm
- Incorrect
- Needs context
- Skip

Disable the action while submitting, use an idempotency key, show the appended decision after success and retain the original model output. If the API fails, preserve the user’s unsent choice locally and offer Retry; do not pretend it saved.

### Insights

- Generated-at time, model and prompt version
- What changed
- Dominant narratives/severity
- Local and global news candidates, separated
- Experimental forecast range or `Insufficient data`
- Coverage note and limitations
- Citations that navigate to filtered metrics/items

Keep Ask Amanah behind a button and cut it before weakening Overview, Explorer or Review.

### Reports

The report builder inherits active URL filters and previews:

- Scope statement
- Coverage and denominators
- Selected KPI/trend/narrative charts
- Reviewed local/global event associations
- Redacted evidence references
- Methodology, model/dataset/tool disclosure and limitations

MVP export actions:

- `Print / Save as PDF` using a print stylesheet
- `Download aggregate CSV`

The UI must state: “This report reflects the selected sources, communities, dates and filters—not the whole platform.”

### Connections

Show purpose, state, last successful check and safe limitation only. Supported states:

- Connected
- Degraded
- Not configured
- Access required
- Institutional approval required
- Fixture only
- Disabled

Never display keys, tokens, raw error bodies or a fake green status.

## 10. Component inventory

### Foundation

- `Logo`
- `Button`
- `Badge`
- `Card`
- `Tooltip`
- `Dialog`
- `Drawer`
- `Skeleton`
- `EmptyState`
- `ErrorState`
- `ContentWarning`

### Layout and navigation

- `MarketingHeader`
- `AppShell`
- `Sidebar`
- `MobileNav`
- `GlobalFilterBar`
- `CoverageStrip`
- `FixtureBanner`

### Analytics

- `KpiCard`
- `TrendChart`
- `VolumeChart`
- `CategoryBars`
- `SignalCard`
- `ForecastCard`
- `NewsAssociationCard`
- `ChartSummary`

### Evidence and review

- `ExplorerTable`
- `ContentPreview`
- `ItemDetailDrawer`
- `ClassificationPanel`
- `ReviewActions`
- `AuditTimeline`

### Reports and operations

- `ReportFilterSummary`
- `ReportPreview`
- `ExportActions`
- `ConnectionStatusCard`

Do not build a large generic design-system library. Implement only components used by the demo path.

## 11. Data and state strategy

- TanStack Query owns server state and cache invalidation.
- URL search parameters own shareable filters.
- Component state owns drawers, dialogs and reveal controls.
- Supabase Auth owns the session; FastAPI receives its bearer JWT.
- Theme/content-safety preferences may use local storage.
- Zod validates fixture and live responses at the API boundary.

Use stable query keys that include all filters:

```text
['overview', from, to, source, community, query, narrative]
['search', q, filters, cursor]
['item', itemId]
['insights', filterHash]
['report', reportId]
```

Changing a global filter invalidates relevant aggregates and preserves the URL as the source of truth.

## 12. HTML presentation workstream

### Format decision

Build the deck as a public/unlisted `/presentation` route inside the same Vite application. Use ordinary React/HTML/CSS, not a heavy presentation dependency. Benefits:

- exact brand consistency;
- easy Netlify deployment;
- deterministic 16:9 recording;
- keyboard navigation;
- print/PDF fallback;
- reusable live dashboard screenshots/components.

Slides must not query live APIs during recording. Use frozen synthetic/redacted data so numbers and screenshots remain stable.

### Presentation controls

- Left/right arrow, Space and Page Up/Page Down navigation
- Slide number and progress indicator
- Fullscreen button
- `?slide=4` direct link
- Presenter notes hidden from recording view
- `prefers-reduced-motion` support
- Print stylesheet with one 16:9 slide per page

### Recommended 9-slide story

1. **Title — A trust we carry together:** Project Amanah and tagline.
2. **What Amanah asks of us:** mutual care, enjoining good, resisting wrong and disciplined protective concern for the deen; translate each idea into plain language.
3. **Why this matters:** isolated incidents, cumulative burden and normalization/desensitization concern; the goal is concern without sensationalism.
4. **The gap and solution:** feeds show incidents; Amanah turns a bounded sample into Capture → Classify → Contextualize → Human review → Learn/report.
5. **How it works:** source/query registry, normalization, model, Supabase/API and dashboard at a high level.
6. **Product demonstration:** transition to live/recorded Overview → chart drill-down → Explorer → review.
7. **Deeper analysis:** narratives, local/global events and carefully bounded forecast commentary.
8. **Amanah in practice:** synthetic/redacted data, no identity profiling, justice in classification, restraint in collection, human oversight, limitations and disclosure.
9. **Impact and invitation:** who benefits, what the hackathon proves, the connector roadmap and “Carry the trust with care.”

### Timing for a 3–5 minute video

- Slides 1–4: approximately 60–75 seconds total
- Architecture slide: approximately 20 seconds
- Product demonstration: approximately 90–150 seconds
- Analysis/responsible design: approximately 45–60 seconds
- Closing: approximately 15–20 seconds

Write the narration in `presentation/transcript.md` before final recording. Use it for accurate captions and keep on-screen claims synchronized with the demonstrated fixture data.

Explain each Arabic/Islamic term in plain English the first time it appears. The transcript should make clear that faith motivates care, disciplined evidence and responsible action; it does not authorize coercion, vigilantism, religious judgment or surveillance. Have the final faith-language passages reviewed by a trusted scholar/community advisor when possible.

### Recording safeguards

- Turn off personal notifications and browser autofill.
- Use a clean invited demo account.
- Hide bookmarks, unrelated tabs and developer secrets.
- Preload the app and presentation.
- Record at 1920×1080 or another 16:9 size.
- Keep a screen recording and static slide/PDF fallback.
- Do not reveal real hateful material or personal information.

## 12A. Suggested frontend tickets

Create these as small, sequential tasks. Each ticket should leave the deployed preview in a working state.

1. **FE-01 — Brand tokens and logo assets**  
   Deliver SVG variants, favicon, typography, colors and global CSS tokens.

2. **FE-02 — Typed API/fixture boundary**  
   Deliver contracts, Zod validation, fixture/live providers and the visible fixture banner.

3. **FE-03 — Router, auth and application shell**  
   Deliver public/protected routes, invited login, logout, sidebar/topbar and mobile navigation.

4. **FE-04 — Marketing page**  
   Deliver the faith-rooted Amanah-to-problem-to-solution narrative, responsible-use section and login path.

5. **FE-05 — Overview coverage and KPIs**  
   Deliver coverage strip, scoped KPI cards, definitions and loading/empty/error states.

6. **FE-06 — Overview charts and drill-down**  
   Deliver trend/volume/category charts, accessible summaries and Explorer filter URLs.

7. **FE-07 — Explorer search and table**  
   Deliver autocomplete, filter chips, cursor table, sorting and content-safe previews.

8. **FE-08 — Item drawer and human review**  
   Deliver context/provenance, reveal controls, review mutation, retry and audit history.

9. **FE-09 — Insights and citations**  
   Deliver cached analysis, event/forecast caveats and evidence-navigation links.

10. **FE-10 — Report preview and aggregate CSV**  
    Deliver immutable-filter summary, print CSS, disclaimer and authorized CSV action.

11. **FE-11 — Connections and methodology**  
    Deliver truthful integration states, disclosure, tools/datasets/licenses and limitations.

12. **FE-12 — Prepared Meme Signals**  
    Deliver three blurred synthetic/redacted examples only if FE-01 through FE-11 are stable.

13. **FE-13 — HTML presentation and transcript**  
    Deliver the nine-slide route, controls, frozen metrics/screenshots, print mode and narration.

14. **FE-14 — Accessibility, resilience and Netlify release**  
    Deliver keyboard/mobile/reduced-motion checks, fallback tests, final deployment and recording readiness.

## 13. 48-hour execution schedule

### Hours 0–3 — story, contract and brand lock

- Confirm the P0 demo path with backend contributor.
- Freeze the one-paragraph Amanah story and its ethical boundary before writing page or presentation copy.
- Freeze fixture response shapes.
- Select logo concept and create core SVG assets.
- Implement color/type/spacing tokens.
- Scaffold routes, API provider and fixtures.

**Exit:** marketing and app shells render with final brand; fixture `/v1/overview` equivalent validates.

### Hours 3–9 — marketing, auth and shell

- Build the full marketing narrative.
- Add login/logout and protected routes.
- Build sidebar/topbar/global filter shell.
- Deploy the first Netlify preview.

**Exit:** public → login → protected fixture Overview works from a clean browser.

### Hours 9–19 — Overview

- Coverage strip and KPI cards.
- Trend, volume and category charts.
- Signals, data warnings and accessible summaries.
- Chart clicks produce correct Explorer URLs.

**Exit:** every metric has a denominator/scope and every chart drills down.

### Hours 19–27 — Explorer and review

- Search/autocomplete and filters.
- Table, cursor states and item drawer.
- Review action, retry and audit history.
- Content warnings and redaction controls.

**Exit:** one synthetic item moves from chart to evidence to appended review.

### Hours 27–33 — Insights, report and connections

- Cached Insights response with citations.
- Print-report preview and aggregate CSV.
- Honest connector states.
- Add three prepared Meme Signals cards if time remains.

**Exit:** active filters persist into the report and every unavailable connector is labelled honestly.

### Hours 33–38 — live backend integration

- Replace fixture provider with live provider.
- Reconcile OpenAPI/types once.
- Test auth, CORS, cursors, errors and review idempotency.
- Keep visible fixture fallback.

**Exit:** deployed frontend completes the P0 path against FastAPI or visibly falls back.

### Hours 38–43 — HTML presentation

- Build nine slides.
- Add frozen screenshots/metrics.
- Write transcript and presentation controls.
- Rehearse live-demo transition.

**Exit:** the deck runs offline/online, at 16:9, with keyboard navigation and complete narration.

### Hours 43–47 — QA and recording

- Mobile, keyboard, contrast and reduced-motion checks.
- Loading/empty/error/access-required/fixture cases.
- Cross-browser smoke test.
- Record the captioned demonstration and backup version.

**Exit:** demo succeeds twice from a clean browser with external services unavailable.

### Hour 47–48 — freeze

- No new features.
- Fix only demo-blocking defects.
- Verify Netlify URL, login, presentation URL and backup assets.
- Finalize disclosure and known-limitations copy.

## 14. Integration checkpoints with backend contributor

### Checkpoint A — hour 3

- Endpoint list and response fixtures agreed
- Auth approach agreed
- Enums/errors/time format agreed

### Checkpoint B — hour 12

- `/healthz`, `/v1/overview` and one item response callable
- CORS works from Netlify preview/local Vite
- Fixture and live shapes match

### Checkpoint C — hour 24

- Search/filter/cursor response works
- Item detail and review append work
- Safe error states documented

### Checkpoint D — hour 32

- Insights, Connections and report responses frozen or fixture-backed
- No more breaking API changes without explicit coordination

If an endpoint misses its checkpoint, keep the corresponding feature fixture-backed and label it. Do not rewrite the UI around an unstable backend at the expense of the working demo path.

## 15. Frontend test checklist

### Functionality

- Marketing → login → dashboard route works
- Protected route redirects unauthenticated visitors
- Logout clears access and returns to public route
- Overview filters update queries and URL
- Chart click opens Explorer with exact filters
- Search debounce and stale-request cancellation work
- Cursor pagination does not duplicate rows
- Item drawer supports direct URL/reload where needed
- Review action cannot double-submit
- Report snapshot preserves filters and disclosure
- Fixture banner is always visible in fixture/fallback mode

### Safety and privacy

- No keys/tokens/service-role values appear in browser bundle or network responses
- Harmful text/media is collapsed or blurred by default
- No public author search/ranking exists
- No real harmful or personal content exists in committed fixtures/slides
- External source links use safe new-tab attributes
- HTML/source text is escaped; no `dangerouslySetInnerHTML` for collected content

### Accessibility

- Complete keyboard path through login, filters, charts, table, drawer and review
- Visible focus indicators
- Screen-reader labels for chart summaries and controls
- Color is never the only status indicator
- Body/UI contrast meets WCAG AA
- Reduced motion works
- Touch controls remain usable at mobile sizes
- Arabic/RTL fixture renders in correct direction if included

### Presentation

- 16:9 layout at 1920×1080
- Arrow/Space navigation and direct slide links work
- No layout shift from fonts/images
- Transcript matches claims and fixture numbers
- Captions are accurate
- Static/PDF and recorded fallbacks exist

## 16. Definition of frontend done

The frontend is done when a clean browser can:

1. Understand that Amanah means a shared trust, why that matters to the mission, and how it becomes careful product behavior.
2. Log in with the invited account.
3. See scoped metrics with denominators and coverage.
4. Click a spike and land on correctly filtered supporting records.
5. Inspect one redacted synthetic record with context and provenance.
6. Append a human review decision without losing the model result.
7. Preview a report that retains the selected platform/community/date filters.
8. See which integrations are live, fixture-backed or access-gated.
9. Open and present the complete HTML slide deck.
10. Complete the same path when external services fail by using visibly labelled fixtures.
