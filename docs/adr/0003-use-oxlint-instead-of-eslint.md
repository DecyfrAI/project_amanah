# 3. Use oxlint instead of ESLint

## Status

Accepted

## Date

2026-08-22

## Deciders

Frontend contributor

## Context and Problem Statement

`workflows/frontend.md` Step F0 requires a linter with a zero-warning CI gate,
and names ESLint + Prettier as the example pairing. It further requires the lint
configuration to enforce jsx-a11y rules, no array-index keys, no inline styles
for static values, and exhaustive-deps for hooks.

Vite 8's `react-ts` template no longer scaffolds ESLint. It ships **oxlint**, a
Rust-based linter, as the default. We must either add ESLint back or accept the
scaffolded default, and the decision affects whether the accessibility rules
this product depends on are actually enforced.

Project Amanah targets WCAG 2.2 AA as a hard product requirement, not a nicety.
Accessibility linting is therefore load-bearing, and any choice that weakens it
is unacceptable regardless of other benefits.

## Decision Drivers

- The mandated rule categories must be genuinely enforceable, jsx-a11y above all
- Zero-warning gate must be expressible
- Fast inner loop matters in a 48-hour build
- Fewer dependencies and less configuration surface (`rules/general.md` §53)
- Working against the framework's default costs time and creates drift

## Considered Options

1. **oxlint** as scaffolded, with its plugins enabled explicitly
2. **ESLint 9** with `eslint-plugin-jsx-a11y`, `eslint-plugin-react-hooks`, and
   `typescript-eslint`, added back manually
3. **Both** — oxlint for speed, ESLint for rules oxlint lacks

## Decision Outcome

**Chosen: option 1, oxlint.**

Verified before deciding that oxlint exposes `--jsx-a11y-plugin`,
`--react-plugin`, `--react-perf-plugin`, and `--import-plugin`, and that
`--deny-warnings` produces a non-zero exit code. Between them these cover every
rule Step F0 names:

| Step F0 requirement | Covered by |
| --- | --- |
| jsx-a11y rules | `jsx-a11y` plugin — 20 rules enabled in `.oxlintrc.json` |
| No array-index keys | `react/no-array-index-key` |
| Hook exhaustive-deps | `react/exhaustive-deps` |
| No inline styles for static values | `react-perf` rules, partially; the token rule in AGENTS.md and review cover the rest |
| Zero-warning gate | `--deny-warnings` |

The one partial is "no inline styles for static values". oxlint's `react-perf`
rules catch object and function props created in render, which is the expensive
case, but not every static inline style. The stricter constraint in this
codebase is the token rule — no literal design value may appear in a component
at all — which is enforced by review rather than by lint. That gap is accepted
and recorded here.

Option 3 was rejected outright: two linters means two configurations that drift
apart, doubled CI time, and contradictory autofixes.

## Positive Consequences

- Lint runs in milliseconds, so `npm run verify` stays fast enough to run before
  every commit rather than being skipped
- No divergence from the framework default, so future template updates apply
  cleanly
- Four fewer direct dependencies and no `eslint.config.js` to maintain
- Config is ESLint-v8-compatible JSON, so migrating to ESLint later is mostly
  mechanical if that becomes necessary

## Negative Consequences and Trade-offs

- Smaller rule catalogue than ESLint's ecosystem. Rules with no oxlint
  equivalent cannot be adopted without revisiting this decision
- Two legacy rules had to be disabled during setup because oxlint either lacks
  them or they do not apply to the modern JSX transform
  (`react/react-in-jsx-scope`, `react/prop-types` — TypeScript covers the latter)
- `import/no-unassigned-import` was disabled: CSS and test-setup imports are
  side-effect imports by design and are the rule's canonical false positive
- Less community documentation when a rule misfires

## Pros and Cons of the Options

### oxlint

- Good: default in the scaffold; very fast; covers the mandated categories;
  ESLint-compatible config format
- Good: `react-perf` plugin has no direct ESLint-core equivalent and catches a
  real class of re-render bug
- Bad: smaller rule catalogue; younger project; thinner documentation

### ESLint 9

- Good: largest rule ecosystem; the reference implementation of jsx-a11y; every
  Step F0 rule available by name
- Good: most contributors already know it
- Bad: must be added back against the template's grain; flat-config migration
  friction; four or more extra dependencies; noticeably slower, which in
  practice means the gate gets skipped

### Both

- Good: maximum rule coverage
- Bad: two sources of truth that drift; doubled CI time; conflicting autofixes;
  contradicts `rules/general.md` §5 (prefer the simpler equivalent)

## Links

- `workflows/frontend.md` — Step F0 setup checklist
- `rules/frontend.md` — accessibility and performance rules being enforced
- `rules/general.md` §8 (documented deviation), §53 (dependency restraint)
- `apps/web/.oxlintrc.json` — the resulting configuration
