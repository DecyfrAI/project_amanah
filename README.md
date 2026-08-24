# Project Amanah

A human-in-the-loop research observatory for public anti-Muslim hate online.

Amanah collects public material from reviewed sources, separates *"is this about
Muslims or Islam?"* from *"is this hostile?"*, computes its figures in SQL rather
than in a language model, and shows every rate beside the numerator, denominator,
date window, and coverage it came from. A classification is a proposal for human
review, never a verdict.

---

## The problem

Anti-Muslim hate online is widely reported and poorly measured. Advocacy groups
and researchers can point at incidents but struggle to say how much, where, in
what form, and whether it is changing — because the underlying material is
scattered, the platforms' own tooling is not built for research, and most
automated approaches conflate *talking about Muslims* with *attacking Muslims*.

That conflation is the central failure. A model that flags Muslim-related
vocabulary as hateful will flag a mosque's opening-hours post, a news report on a
hate crime, and someone quoting an abuser in order to condemn them. Amanah treats
relevance and hostility as two separate stages for exactly this reason.

## Who this is for

Researchers, advocacy caseworkers, and trust-and-safety practitioners who need a
defensible figure with its scope attached — not a dashboard that produces a
number nobody can reproduce.

## What it does

- **Collects** from reviewed RSS news feeds, the official YouTube API, and
  reviewed open datapacks. No scraping; no source runs without review.
- **Classifies** in two stages through a controlled Gemini boundary: relevance
  first, then stance and hate type against a versioned taxonomy.
- **Counts** deterministically. Every metric is SQL. Gemini may *explain* a
  stored figure and must cite it; it never produces one.
- **Reviews.** A reviewer confirms or corrects a classification, and the decision
  is appended beside the model output rather than overwriting it.
- **Assists reporting.** Amanah shows the platform's own reviewed policy with its
  version and official link, and saves what you prepared. **It never submits a
  report.**
- **Exports** immutable research snapshots with coverage, denominators,
  citations, methodology version, and limitations attached.

## What it deliberately does not do

- No person-level search, ranking, identity resolution, or repeat-offender views.
- No automated report submission to any platform, and no arbitrary destinations.
- No browser call to Gemini or any secret-backed provider.
- No claim of platform-wide prevalence from a monitored sample.
- No inference of religion, ethnicity, or real-world identity.

---

## The AI / human boundary

This is the line the whole design defends:

| Concern | Owner |
|---|---|
| Every count, rate, denominator, and trend | Deterministic SQL |
| Relevance and hate-type proposals | Gemini, server-side, schema-validated |
| Narrative summaries of stored figures | Gemini, with every number cited against a stored fact bundle |
| Confirming or correcting a classification | A human reviewer |
| Deciding a policy applies, and filing a report | The user, never the system |

A narrative whose citations fail verification is discarded, and the page keeps
its figures. If Gemini is unavailable, over budget, or returns invalid output,
the deterministic metrics are unaffected — the prose is simply absent, with a
stated reason.

## Architecture

```
Browser (React + Vite + TypeScript)
  │  Supabase access token as  Authorization: Bearer …
  ▼
FastAPI  /v1  (every route authenticated; only /healthz and /readyz are open)
  ├── domain services ── deterministic metrics (SQL)
  ├── controlled Gemini boundary (budgets, caches, schema validation, citations)
  ├── repositories ──── PostgreSQL (Supabase) + row-level security
  └── private object storage (short-lived signed URLs; bytes never in Postgres)
        ▲
        │  ETL: reviewed RSS · YouTube official API · reviewed open datapacks
```

Contract direction is one-way: the OpenAPI/Pydantic models in `backend/` are the
source of truth, and the frontend validates live responses against mirrored Zod
schemas in [`apps/web/src/api/wire.ts`](apps/web/src/api/wire.ts) before mapping
them into view models. Deeper diagrams live in
[`docs/architecture/`](docs/architecture/).

### Stack

React 19, Vite, TypeScript, TanStack Query, Zod · FastAPI, Pydantic, SQLAlchemy,
Alembic · PostgreSQL with Supabase Auth and Storage · Gemini · Render (API),
Netlify (web), GitHub Actions (CI and ETL).

---

## Live, fixture, and mock inventory

Nothing in this product silently substitutes fixture data for a failed live call.
A live failure stays a visible failure, and every fixture surface is labelled on
screen.

| Surface | State |
|---|---|
| Supabase sign-in, session restore, bearer tokens, logout | **Live** |
| News (`/v1/news`) | **Live** — 32 articles ingested from 4 reviewed publishers |
| Dashboard, items, filters | **Live** |
| Item detail with full model disclosure | **Live** |
| Grounded assistant | **Live**, needs `GEMINI_API_KEY` |
| Insights, discussion, reactions, captures | **Live** |
| Policy analysis, prepared reports | **Live** |
| Contributions history | **Live** |
| Research-report snapshot, aggregate CSV, print/PDF | **Live** |
| Image catalogue and classification of a catalogued image | **Live**, needs `SUPABASE_STORAGE_SECRET_KEY`; reports itself unavailable without one |
| Authenticated image upload to private storage | **Live** - cleaned, EXIF-stripped, owner-only |
| Gemini classification of an upload | **Live**, needs `ALLOW_THIRD_PARTY_CONTENT_INFERENCE=true` and a Gemini key |
| Review queue, Connections walkthrough | **Mock**, labelled in place |
| Settings table density | **Mock**, labelled; the media preference beside it is real |

`VITE_DATA_MODE` selects the provider: `fixture` (all synthetic), `live` (all
real), `demo` (the hackathon hybrid — product data live, remaining mocks labelled
and never used as a fallback), or `fallback` (legacy try-live-then-fixture with a
visible banner).

### Known gaps

- **Discussion attachments were deliberately excluded** (PA-05, descoped 24
  August 2026). Text notes work on both viewer snapshots and machine-generated
  insights, and first-party chart captures can be attached. Arbitrary uploads
  into a shared thread were left out for **safety, not time**: they would need
  malware scanning, safe download handling, and per-attachment authorization,
  and ADR 0004 refused a screenshot board because it would redistribute the
  material this product exists to measure. The reasoning is recorded in
  `docs/completion-guide.md`.
- **Gemini is not configured**, so classification and the assistant report
  themselves unavailable rather than guessing. News is ingested but unclassified:
  items show `is_classified: false` and no hate label, which is the honest state.
- **Uploaded images are not sent to the model unless the deployment opts in.**
  `ALLOW_THIRD_PARTY_CONTENT_INFERENCE` is off by default, so upload and private
  storage work while classification of an upload reports itself unavailable. An
  upload is the uploader's material, not this product's, so forwarding it is a
  deliberate choice rather than a default.

---

## Prerequisites

- Node.js 22+ and npm
- [uv](https://docs.astral.sh/uv/) 0.11+ (installs Python 3.13 itself)
- A Supabase project (Auth, Postgres, Storage)
- A Gemini API key, for the classification and assistant paths

## Quick start

Backend, from the repository root:

```bash
uv sync --locked --project backend --all-groups
```

Copy the template and fill it in — never commit a populated `.env`:

```bash
cp backend/.env.example backend/.env
```

Apply migrations as a one-off process (never from application startup):

```bash
uv run --project backend --env-file backend/.env alembic -c backend/alembic.ini upgrade head
```

Run the API:

```bash
uv run --project backend --env-file backend/.env uvicorn amanah.main:create_app --factory --reload
```

Frontend, in a second terminal:

```bash
npm --prefix apps/web install
```

```bash
npm --prefix apps/web run dev
```

The web app serves on http://localhost:5173 and the API on http://127.0.0.1:8000.
With no `.env` at all the frontend runs entirely on committed fixtures.

## Tests and gates

```bash
npm --prefix apps/web run verify
```

That is format check, lint, type check, and the 354-test frontend suite.

```bash
uv run --project backend pytest backend/tests
```

That runs 536 tests and reports 401 as skipped. The skipped ones are the
database, migration, constraint, and RLS suite; to run all 937, point the suite
at a Postgres server it may create and drop scratch databases on:

```bash
AMANAH_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres uv run --project backend pytest backend/tests
```

On PowerShell:

```bash
$env:AMANAH_TEST_DATABASE_URL='postgresql://postgres:postgres@localhost:5432/postgres'; uv run --project backend pytest backend/tests
```

A disposable container is enough, and is what these were verified against:

```bash
docker run -d --name amanah-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

## Demo walkthrough

1. Open the marketing page anonymously — no product API call is made.
2. Open a protected route and be redirected to login.
3. Sign in, then refresh to prove the session is restored.
4. Open News: one article from the selected reviewed feed, labelled publisher
   context, carrying no Amanah hate classification.
5. Open the datapack view: source and platform read `N/A`, with dataset
   provenance and sampling limits stated separately.
6. Ask the assistant a starter question and read its citations and limitations.
7. Prepare one platform report: choose a policy, confirm its version, save it,
   and see that Amanah did not submit it.
8. Generate a research snapshot, download its CSV, open the print view.
9. Show an image unblurred, enable blur in Settings, and watch Explorer update
   immediately.
10. Start an insight from an Overview figure, then use **View all insights** to
    find it in the list.
11. Open a mock surface and read its label.
12. Log out and confirm the protected data is gone.

---

## Documentation

| Topic | Document |
|---|---|
| Product behaviour and API scope | [`docs/spec.md`](docs/spec.md) |
| Remaining work for the demo | [`docs/completion-guide.md`](docs/completion-guide.md) |
| Deployment procedure | [`docs/runbooks/deployment.md`](docs/runbooks/deployment.md) |
| Operations | [`docs/runbooks/operations.md`](docs/runbooks/operations.md) |
| Architecture decisions | [`docs/adr/`](docs/adr/) |
| Threat model | [`docs/architecture/backend-threat-model.md`](docs/architecture/backend-threat-model.md) |
| Reviewed news sources | [`docs/news-rss-sources.md`](docs/news-rss-sources.md) |
| Frontend detail | [`apps/web/README.md`](apps/web/README.md) |
| Backend detail | [`backend/README.md`](backend/README.md) |
| Binding engineering rules | [`AGENTS.md`](AGENTS.md), [`rules/`](rules/) |

## Repository must stay private

`apps/web/public/media/fixtures/memes/` holds a sourced research corpus of
hostile image memes, marked `internal-research-fixture-not-for-redistribution`
under [ADR 0007](docs/adr/0007-research-image-corpus.md). It must be removed
before this repository could ever be made public, and it must never reach a
public bucket or a build artifact.

## Limitations

Every figure describes **the monitored sample**, not a platform, a country, or a
group of people. Coverage is uneven, sources are a reviewed subset, the seeded
sample is deliberately enriched for relevance, and days without collection are
reported as gaps rather than as zero. Model output is a proposal, not a finding.
None of this supports a prevalence claim, and the interface is built to keep that
distinction visible rather than to hide it.
