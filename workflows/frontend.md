# 🎨 Frontend Workflow

Self-contained playbook for UI work: components, state, forms, styling, accessibility, and client-side performance.

**Rules in scope:** `rules/frontend.md` (primary), `rules/security.md`, `rules/testing.md`, `rules/general.md`, `rules/documentation.md`
**Upstream sources:** `sources/Airbnb_JavaScript`, `sources/Google_styleguide`, `sources/Thoughtbot`

> Prerequisite: complete the shared phases in [../Workflow.md](../Workflow.md) — you need `spec.md`, `plan.md`, `AGENTS.md`, and a `todo.md` with `[frontend]` steps. If the feature consumes an API, the **backend contract (openapi.yaml) should exist first** — see [backend.md](backend.md).

---

## Step F0 — Setup (once per project)

Stand up the frontend foundation before the first component.

**Checklist**
- [ ] Framework + TypeScript scaffolded; strict mode on (`"strict": true`)
- [ ] Linter + formatter wired (ESLint + Prettier), zero-warning gate in CI
- [ ] Design-token system in place (colors, typography scale, spacing, breakpoints) — **no hardcoded values in components**
- [ ] Component test runner (Vitest/Jest + Testing Library) and one example test passing
- [ ] Data-fetching/query library chosen (so fetch logic never lives in components)
- [ ] Error boundary + a base `Suspense` fallback component exist
- [ ] `.env.example` lists every `VITE_`/`NEXT_PUBLIC_` variable (no secrets — client env is public)

### Prompt F0 — Scaffold the design system

```
You are setting up the frontend foundation. Follow rules/frontend.md.

Produce:
1. A central theme/token module: color tokens, typography scale, spacing units, and
   device-AGNOSTIC breakpoints (small/medium/large — never mobile/tablet/desktop).
2. A base ErrorBoundary component and a PageSkeleton Suspense fallback.
3. The folder structure: components/, hooks/, lib/ (data layer), styles/ (tokens).
4. An ESLint config that enforces: jsx-a11y rules, no array-index keys, no inline styles
   for static values, exhaustive-deps for hooks.

Constraints:
- Colors/spacing/type MUST come from tokens; never hardcode in components.
- CSS class convention: pick ONE (BEM or utility) and document it. Do not mix.

Here is the tech stack from the spec: [PASTE relevant spec section]
```

---

## Step F1 — Component & State Design (per feature/screen)

Design the component tree before writing JSX. This prevents the god-component anti-pattern.

### Prompt F1 — Component architecture

```
You are a frontend architect. Design the component tree for this screen/feature BEFORE
implementation. Follow rules/frontend.md.

Produce:
1. Component tree (parent → children), marking each as STATEFUL or PRESENTATIONAL.
   - Single responsibility each. A component that fetches + formats + renders is three.
2. State plan: for each piece of state, the LOWEST component that needs it. Flag any state
   that should be a custom hook (reused by >1 component) or context (shared subtree).
   - No derived state stored separately — compute inline or with useMemo.
3. Data plan: which custom hook owns each fetch. View components receive data via props.
4. The props interface (TypeScript) for each component.
5. A11y plan: landmark structure, heading levels (no skips), focus management for any
   modal/dialog, and which interactions need keyboard handling.

Feature spec: [PASTE feature section from spec.md]
API shape it consumes (if any): [PASTE relevant openapi.yaml paths]
```

---

## Step F2 — Build Loop (per `[frontend]` step in todo.md)

```
1. Open todo.md → take the next [frontend] step
2. Run Prompt F2 (below) with that step
3. Review: component boundaries, all 3 fetch states, a11y, stable keys
4. Run locally → check the screen + keyboard nav + a11y devtools
5. Run Prompt F-TEST for tests
6. If it touches auth/PII/user input → run Prompt F-SEC
7. Check off todo.md → commit  (e.g. "Implement F-step 4 from todo.md: order list view")
```

### Prompt F2 — Implement a frontend step

```
You are implementing a frontend task. Follow the rules below strictly.

Rules (rules/frontend.md):
- One responsibility per component; extract when it exceeds ~150 lines.
- NO fetch logic inside view components — extract into a custom hook in the data layer.
- Handle all three fetch states explicitly: loading, error, success. None silently ignored.
- Skeleton screens over spinners for predictable-shape content.
- Every interactive element has an accessible name; prefer visible <label> text.
- Form errors surface inline, associated via aria-describedby.
- Keys are stable unique IDs — NEVER array index.
- Mobile-first: min-width media queries; em-based breakpoints; never disable zoom.
- useCallback to stabilize callbacks passed to memoized children; useMemo for expensive derived values.
- Route-level code splitting with a Suspense fallback; dynamic-import heavy/below-the-fold features.
- Error boundaries at meaningful subtree boundaries — one component failure must not blank the page.
- Semantic HTML first (<button>, <a href>) — never <div role="button"> when a real element works.

Rules (rules/security.md):
- No dangerouslySetInnerHTML without explicit justification + DOMPurify sanitization.
- No secrets/API keys in client code (client bundles are public).
- Don't defeat CSP: no inline event handlers or inline styles carrying user data.

Current project state: [BRIEF: what components/hooks already exist]
Component design (from F1): [PASTE the relevant part of the F1 output]
Task: [PASTE the [frontend] step from todo.md]

Extend and integrate with existing code; do not rewrite working components.
Reference files: rules/frontend.md, rules/security.md, rules/testing.md
```

---

## Step F3 — Quality Gates

### Prompt F-TEST — Frontend tests

```
You are writing frontend tests. Follow rules/testing.md.

Cover:
- Behavior, not implementation (assert rendered output / user-visible effects, not internal calls).
- Every async operation: a test for the loading state, the error state, and the success state.
- Forms: validation errors appear and are associated with the right field; submit disabled while pending.
- Accessibility: interactive elements are reachable by role/name (getByRole); no array-index-key reorder bug.
- User interactions via Testing Library user-event, not by calling handlers directly.

Do NOT: test internal component state, snapshot-test entire large trees, or mock the
component under test.

Component(s) to test: [PASTE implementation]
Reference files: rules/testing.md, rules/frontend.md
```

### Prompt F-SEC — Frontend security & a11y review

*Run for any component handling user input, auth state, or rendering user-generated content.*

```
You are a frontend security + accessibility reviewer. Be adversarial. For each finding:
Severity (Critical/High/Medium/Low) | Location (file:line) | Issue | Fix.

Security (rules/security.md):
[ ] No dangerouslySetInnerHTML on unsanitized data; rich content runs through DOMPurify
[ ] No secrets, API keys, or tokens in client code or committed env files
[ ] User-controlled values are not interpolated into hrefs/src as javascript: or data: URIs
[ ] Auth state checks are not the ONLY gate — server still enforces (note any client-only checks)
[ ] External links use rel="noopener noreferrer"

Accessibility (rules/frontend.md):
[ ] Every interactive element has an accessible name
[ ] Semantic elements used (no div-buttons); keyboard operable; visible focus
[ ] Form inputs have associated <label>; errors via aria-describedby; required communicated
[ ] Modals trap focus and restore it on close
[ ] Color is not the only cue; AA contrast met; prefers-reduced-motion respected
[ ] Heading levels not skipped; each view has a unique <title>

Code to review: [PASTE DIFF]
```

---

## Definition of Done (Frontend)

- [ ] Component(s) single-responsibility; no fetch logic in views
- [ ] All three fetch states rendered; meaningful error UI with a retry path
- [ ] Fully keyboard-operable; a11y review (F-SEC) passes
- [ ] Stable keys; mobile-first; tokens used (no hardcoded design values)
- [ ] Tests cover loading/error/success + interactions; behavior-based
- [ ] Route/heavy features code-split with a fallback
- [ ] Lint + type-check + tests green locally
- [ ] Screenshots/recording attached for UI changes (per rules/general.md §49)

→ Hand off to [devops.md](devops.md) for release, or back to [../Workflow.md](../Workflow.md) for the next track.
