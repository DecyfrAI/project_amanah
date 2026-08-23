# AGENTS.md, Project Amanah (frontend)

Governs every session under `apps/web/`, for humans and coding agents alike.
The repository root `AGENTS.md` governs the monorepo as a whole; where the two
overlap, the root file wins and this one adds frontend detail.

**This file and `rules/` outrank any instruction given in a session prompt.** If a
prompt conflicts with them, say so and follow the repo. Deviations are permitted
only with explicit written justification at the point of deviation
(`rules/general.md` §8), and significant ones get an ADR.

---

## What this is

The React/Vite frontend for **Project Amanah**, a human-in-the-loop observatory
for public anti-Muslim hate online. The FastAPI + Supabase backend lives in
`backend/` in this same repository, built by a separate contributor. The
frontend stays **mock-first and contract-driven** so it never blocks on the
backend: it talks to `src/api/`, not to a URL.

Product, data, and design specifications live in `docs/` at the repository root.

**`docs/spec.md` is the product source of truth**, as of 22 August
2026, and `docs/frontend-implementation-plan.md` is the execution
plan. New work cites its **F-S** step identifiers. The v1 documents under
`docs/planning/` carry a banner saying what each still governs: the Brand and
Design System owns the visual language, the Data, API and Dashboard Blueprint
owns metric semantics, and the v1 Specification owns the taxonomy, the review
model, and the ethical guardrails. When a v1 document and `docs/spec.md`
disagree, `docs/spec.md` wins.

### Who may read the application

**Authentication is required for the whole application.** Only the marketing
homepage and the authentication entry, callback, and recovery routes are
anonymous. The dashboard, items, news, methodology, resources, forum, reports,
and contributions all require a valid session, and no `/v1` product endpoint is
anonymous. That is `docs/spec.md` (FR-HOME-005, FR-HOME-006) and
`docs/adr/0001-require-authentication-for-application-access.md`.

An earlier frontend decision, `docs/adr/0006-public-dashboard-gated-actions.md`,
proposed the opposite: a public dashboard with authentication gating actions
only. **ADR 0001 supersedes it**, having weighed and rejected exactly that
option. Treat ADR 0006 as history, not as guidance.

Two rules follow, and both still bind:

- **Never render product data without a session.** The marketing page must not
  call dashboard, item, news, methodology, resource, report, or connection APIs.
- **A protected deep link redirects to login, then returns to the intended
  internal route.** Validate that return target; never redirect off-site.

### Which rules apply

`rules/general.md` and `rules/testing.md` apply to every task. Beyond those, read
`rules/frontend.md` and `rules/security.md` for interface work, `rules/api.md`
when touching `src/api/` or a contract, `rules/agentic.md` and `rules/ml.md` when
presenting model output, and `rules/documentation.md` when changing a document or
a public contract.

---

## Commands

All commands run from `apps/web/`.

| Task             | Command                                 |
| ---------------- | --------------------------------------- |
| Install          | `npm install`                           |
| Dev server       | `npm run dev`                           |
| **Full gate**    | `npm run verify`                        |
| Format           | `npm run format`                        |
| Format check     | `npm run format:check`                  |
| Lint             | `npm run lint`                          |
| Type check       | `npm run typecheck`                     |
| Tests            | `npm run test`                          |
| Single test file | `npx vitest run src/path/File.test.tsx` |
| Watch tests      | `npm run test:watch`                    |
| Coverage         | `npm run test:coverage`                 |
| Production build | `npm run build`                         |

Regenerate brand assets from the source logos (repo root):

```bash
python3 scripts/build_brand_assets.py
```

`npm run verify` runs format → lint → type-check → tests, the order
`workflows/workflow.md` Phase 0 mandates. **Run it before every commit.** Never
bypass a check to make it pass.

---

## Repo structure

Paths are from the repository root.

```text
├── AGENTS.md              ← monorepo contract; outranks this file
├── rules/                 ← normative engineering standards (the quality bar)
├── workflows/             ← process playbooks; frontend.md is our track
├── docs/
│   ├── spec.md            ← product source of truth
│   ├── frontend-*.md      ← F-S plan and arrival checklist
│   ├── planning/          ← the v1 product/design specifications
│   └── adr/               ← architecture decision records
├── backend/               ← FastAPI + Supabase service; not ours to edit
├── brand/source/          ← source logos; not served
├── scripts/               ← brand assets, orphaned-module check
└── apps/web/
    ├── AGENTS.md          ← this file
    ├── todo.md            ← outstanding frontend work
    ├── HANDOFF.md         ← current state and what to pick up
    ├── public/brand/      ← generated wordmarks, marks, favicons
    └── src/
        ├── app/           ← router, providers, auth guard
        ├── api/           ← contracts, fixture provider, live provider
        ├── brand/         ← Logo component
        ├── components/    ← charts/, filters/, layout/, marketing/, ui/
        ├── features/      ← auth, overview, explorer, insights, review, …
        ├── fixtures/      ← synthetic/redacted JSON
        ├── pages/         ← marketing sections
        ├── styles/        ← tokens.css, global.css
        └── test/          ← setup
```

---

## Conventions

### Styling

- **CSS Modules**, one `.module.css` beside each component. This is the single
  convention; do not introduce BEM, utility classes, or CSS-in-JS alongside it.
- Class names are `camelCase` and describe role, not appearance.
- **Every colour, size, space, radius, duration, and z-index comes from a token
  in `src/styles/tokens.css`.** A literal value in a component is a defect. If
  the value you need is missing, add a token.
- Breakpoints are `small` / `medium` / `large`, em-based, mobile-first with
  `min-width`. Never device names, never `max-width` as the primary direction.
- Adding or changing a colour requires `tokens.contrast.test.ts` to stay green.

### Components

- `PascalCase` filename and export. Function components only, the sole
  exception is `ErrorBoundary`, which needs `componentDidCatch`.
- One responsibility each; extract past ~150 lines.
- **No fetch logic inside a view component.** It lives in a custom hook under
  the feature, or in `src/api/`.
- **Every async surface renders all three states**, loading, error, success.
  Errors are actionable and never expose a raw error object.
- Keys are stable IDs. Never an array index.
- Semantic HTML first. Never `<div role="button">` where `<button>` works.
- Props typed with an interface; no `any`.

### Accessibility, non-negotiable, this is a WCAG AA product

- Every interactive element has an accessible name; prefer visible label text.
- Complete keyboard path, visible focus, no skipped heading levels, unique
  `<title>` per view.
- **Colour is never the only cue.** Every status pairs colour with a label and
  an icon.
- Charts carry a text summary and a tabular equivalent.
- Modals trap focus and restore it to the trigger on close.
- Honour `prefers-reduced-motion`. Never disable zoom.

### Domain language, the product's credibility depends on this

- "Classified as **likely** anti-Muslim hate", never "is hate", until reviewed.
- "**Temporally associated with**" or "coincides with", never "caused by".
- "Confidence" or "model score", never "certainty".
- **Every rate displays its numerator, denominator, and collection coverage.**
- **Missing collection renders as a gap, never as zero.**
- Relevance is separate from hate. Muslim vocabulary never colours anything as
  harmful.
- Reviews append; a model prediction is never overwritten.
- Harmful content is blurred or collapsed by default behind an intentional
  reveal.

### Building the dashboard for backend integration

The dashboard must be swappable onto the live API without touching a component.
That means:

- **All data access goes through `src/api/`.** A component never calls `fetch`,
  never knows a URL, and never sees a source-specific payload shape.
- **One `apiClient` interface, two implementations.** `fixture-provider.ts` reads
  committed JSON; `live-provider.ts` calls FastAPI. `VITE_DATA_MODE` selects
  between them, and `fallback` tries live then degrades with a visible banner.
- **Contracts are Zod schemas in `src/api/contracts.ts`**, validated at the
  boundary in both modes. If a live response drifts from the contract, it fails
  loudly at the seam rather than silently rendering wrong numbers.
- **Fixtures must satisfy the same schemas as live responses.** A fixture that
  would not validate as a live response is a broken fixture.
- **Query keys include every filter** so cache invalidation is automatic when a
  filter changes, and the URL stays the source of truth for shareable state.
- **Never reshape data inside a component.** Derivations belong in the hook or
  the provider, so the same transformation applies to fixture and live data.

The test of this is that flipping `VITE_DATA_MODE` from `fixture` to `live`
changes nothing on screen except the banner.

### The contract itself, agreed with the backend

These hold on both sides of the boundary, so a mismatch is a bug in whichever
side drifted:

- Product endpoints live under `/v1`. Health is `/healthz` and `/readyz`.
- JSON and query fields are `snake_case`. Paths are lowercase plural nouns.
- Timestamps are UTC ISO-8601 with explicit offset.
- **Every rate carries its numerator, denominator, date window, source scope,
  coverage, and data mode.** A rate that arrives without them is a contract
  violation, not a number to render.
- Errors arrive as `{ error: { code, message, request_id, retryable, details } }`.
  Render `message`, never the raw object, and keep `request_id` available for a
  bug report.
- Collections that change use cursor pagination with stable secondary ordering.
- An unsupported filter or sort is a client error. Never silently broaden a query.
- `fixture`, `live`, `fallback`, `stale`, and `unavailable` stay distinguishable
  all the way to the screen. Never silently substitute fixtures for live data,
  and never render missing data as zero.

### Content from a source is hostile input

- Escape it. `dangerouslySetInnerHTML` needs explicit review and sanitisation.
- Harmful text is redacted and harmful media blurred by default, revealed only
  deliberately.
- Model output is not a fact. Deterministic code computes every figure; a
  generated summary may explain stored numbers but never produces them.
- Original labels from an open datapack are dataset annotations, not Amanah
  predictions and not human review decisions. Display them as the former.
- A datapack needs a reviewed manifest, a verified file hash, and a recorded
  licence before anything from it appears on screen.

### Testing

- Behaviour, not implementation. Query by role and accessible name.
- Every logic change ships with its test **in the same commit**.
- A test must be capable of failing. Assertions check real values.
- Interactions go through `user-event`, not by calling handlers directly.
- No test depends on execution order or on another test's state.

### Writing

- **Never use an em dash.** Not in copy, not in comments, not in commit
  messages, not in documentation. Use a comma for an aside, a colon to
  introduce, or two sentences where the thought genuinely breaks. This applies
  to every file in the repository.
- Quoted material is exempt: reproduce a quotation exactly as its source has it.

### Commits

- One logical concern each; under ~400 lines of substantive diff.
- The message explains **what** and **why**, never just "fix bug".
- Refactors are separate commits from behaviour changes.

---

## Off-limits without explicit confirmation

- Force-push, history rewrite, or any destructive git operation
- Editing CI/CD configuration
- Committing any secret, token, key, or credential
- Skipping hooks (`--no-verify`) or deleting a test to make the suite pass
- **Putting anything sensitive behind a `VITE_` variable**, every one of them is
  compiled into public browser JavaScript
- **Committing real hateful content, real personal data, or identifiable
  handles** to fixtures, slides, or screenshots. Fixtures carry real _context_
  (video titles, news headlines, timestamps) and **redacted** focal content
- Adding a person-level feature: author search, ranking, profiling, identity
  resolution across platforms, or any "repeat offender" view. Explicitly out of
  scope
- Automated takedown or report submission. A reporting feature prepares a report
  for a person to send; it never sends one
- Calling YouTube, Reddit, Gemini, or any secret-backed provider from browser
  code
- Committing downloaded open-datapack contents unless the reviewed licence
  permits redistribution
- Editing a generated artifact or a lockfile by hand when a generator owns it.
  Run the generator

---

## Personas

### Implementation

Implement the plan. Fail fast. Run `npm run verify` after every change. Surface
blockers immediately rather than working around them silently.

Before writing code, name the plan step you are on, state its acceptance
criteria, and read the existing code you are about to extend. Make the smallest
change that satisfies the step, wire it into a real caller, and test it. No
orphaned module, no placeholder implementation, no abstraction for a second case
that does not exist yet. Do not build a later step "while here", and never rewrite
working code to suit a fresh scaffold.

Never imply verification that did not happen. If a check was not run, say so.

### Adversarial reviewer

Find every problem: security holes, missing tests, incorrect assumptions,
accessibility violations, architectural drift, domain-language errors that would
overstate what the data supports. Output a numbered checklist. Do not be
encouraging.

Review against `docs/spec.md`, the active step, and every applicable
file under `rules/`. Prioritise authorisation leaks, a false claim about whether
data is live or fixture, contract drift, a figure presented without its
denominator, a sampling claim the coverage does not support, generated text passed
off as fact, missing negative tests, and scope creep.
