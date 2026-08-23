# Project Amanah (frontend)

React/Vite frontend for **Project Amanah**, a human-in-the-loop observatory for
public anti-Muslim hate online. The frontend is mock-first and contract-driven:
it talks to `src/api/`, never to a URL, so it does not block on the backend. The
FastAPI + Supabase backend lives in `backend/` in this repository.

Only the marketing homepage and the authentication routes are anonymous. Every
application surface requires a session, per `docs/spec.md` and
`docs/adr/0001-require-authentication-for-application-access.md`.

**Read `apps/web/AGENTS.md` and `rules/` first.** They outrank any session
prompt. Product source of truth: `docs/spec.md`. Outstanding work:
`apps/web/todo.md`.

## Run locally

All commands run from `apps/web/`.

```bash
cd apps/web
npm install
npm run dev
```

The full gate before a commit:

```bash
npm run verify
```

That is format check, lint, type-check, then tests.

Copy `apps/web/.env.example` if you need to change `VITE_DATA_MODE`. Every
`VITE_` value is compiled into browser JavaScript. Never put a service-role
key, provider secret, or database URL there.

## Data mode

| `VITE_DATA_MODE`    | Behaviour                                               |
| ------------------- | ------------------------------------------------------- |
| `fixture` (default) | Reads committed synthetic/redacted JSON                 |
| `live`              | Calls FastAPI at `VITE_API_BASE_URL`                    |
| `fallback`          | Tries live, then degrades with a visible fixture banner |

Flipping the mode must change nothing on screen except the banner.

## Research image fixtures

`apps/web/public/media/fixtures/memes/` holds sourced research examples of
hostile image memes. That is an explicit, documented deviation
(`docs/adr/0007-research-image-corpus.md`). The pack is
`internal-research-fixture-not-for-redistribution`. Keep this GitHub repository
**private**. The catalog is behind a session, and images stay blurred until a
person reveals them.

## Layout

Paths are from the repository root.

```text
AGENTS.md                 monorepo contract
rules/                    engineering standards
docs/spec.md              product source of truth
docs/frontend-*.md        F-S plan and arrival checklist
docs/adr/                 architecture decision records
backend/                  FastAPI + Supabase service
apps/web/                 Vite + React 19 application
apps/web/AGENTS.md        frontend contract
apps/web/todo.md          outstanding frontend work
```
