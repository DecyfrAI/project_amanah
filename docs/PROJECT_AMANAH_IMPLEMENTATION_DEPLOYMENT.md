# Project Amanah — Implementation & Deployment Guide

**Version:** 1.2 — 48-hour hackathon edition  
**Recommended 48-hour stack:** React/Vite + TypeScript on Netlify, FastAPI + Python on Render, Supabase/Postgres + Storage/Auth, local or policy-gated hosted inference, GitHub Actions for CI and bounded scheduled ETL

**Companion data and UI contract:** [Data, API & Dashboard Blueprint](./PROJECT_AMANAH_DATA_API_DASHBOARD_BLUEPRINT.md)

**Frontend-only execution plan:** [Frontend Development Plan](./PROJECT_AMANAH_FRONTEND_DEVELOPMENT_PLAN.md)

> **Open-datapack addendum (2026-08-22):** The ETL also supports manifest-validated, reviewed Kaggle/other open CSV/JSONL datapacks. Imports fail before content writes on invalid approval, license, hash, encoding, schema, or row identity. Public source/platform is `N/A`, with dataset provenance stored separately. See the authoritative root [`spec.md`](../spec.md).

> **Seed-registry addendum (2026-08-22):** [`PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`](../PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md) supplies candidate Reddit/YouTube seeds and query families for review. Do not parse or schedule the Markdown directly: copy approved entries to versioned runtime configuration with stable keys, caps, language, sampling stratum, and approval metadata.

## 0. Hackathon constraint: optimize for a convincing vertical slice

There are only **48 hours**. Build one credible story end to end; do not attempt the full production architecture in this document during the hackathon.

### The demo to ship

```text
approved/controlled YouTube call or synthetic/redacted fixture
 → comments ingested
 → Muslim-relevance keyword filter
 → local classifier or authorized fixture/hosted structured output
 → Supabase rows
 → Netlify dashboard
 → trend/spike card + one event association
 → reviewer confirms or rejects an example
 → filter-scoped report preview/aggregate CSV
```

Include **three synthetic/redacted/licensed prepared memes** demonstrating image-text interaction. Process them locally, through an explicitly authorized hosted multimodal API, or use disclosed precomputed results. Do not fine-tune a multimodal model, build a queue system, or implement real-time additional-source ingestion during the 48-hour build.

### Ruthless scope

**Must work live:**

- Netlify-hosted React/Vite dashboard
- Supabase database with a small, coherent schema
- One FastAPI service on Render
- YouTube ingestion for a curated list of video IDs, plus a fixture fallback
- Relevance filtering and one local or policy-authorized structured classification call
- Overview metrics, a daily trend, narrative/severity breakdown, item detail, and review action
- Chart-to-Explorer drill-down preserving date/source/community/narrative filters
- Clear model disclaimer, denominators, and collection timestamp

**Demo with prepared data if needed:**

- One detected spike and one GDELT/news association
- Three meme examples, including a benign confounder
- Evidence hash and provenance display
- Print-optimized filtered report and aggregate CSV

**Explicitly defer:**

- Fine-tuning, pgvector clustering, automated narrative naming
- Reddit approval/PRAW and live Bluesky Jetstream
- Live X, Threads, Instagram/Facebook, TikTok and Mastodon adapters
- Autonomous community scouting or person-level activity tracking
- Celery/Redis, distributed workers, complex model registry
- Multilingual support, public/raw evidence exports, full retention automation
- Organization tenancy and production-grade evidence chain of custody

### Safety and submission gates from the supplied participant-briefing images

Treat these as a briefing-derived checklist and confirm final official instructions before submission:

- Build/test with synthetic, redacted or controlled examples and only the context the test needs.
- Do not create new hateful material for prompts or sample data.
- Do not upload real hateful material or personal data to a third-party AI service without explicit authorization.
- Do not expose personal information, profile protected identities, enable doxxing, targeted harassment or surveillance, or collect real abuse the demonstration does not need.
- Disclose AI tools, datasets, outside materials, licenses and earlier work; plainly state limits and human checks.
- Caption the demonstration video or provide an accurate transcript.
- Prepare a concise problem statement, intended users, build description, accessible project link, and safety/privacy/known-limitations statement.

The supplied judging slide weights impact and functionality most heavily. Optimize for one narrow end-to-end workflow that works reliably and visibly handles its limits; innovation, ethics, sustainability and communication still need explicit evidence.

### Vibecoding guardrails

- Start from one monorepo and one shared schema; do not let generated code create parallel data models.
- Give the coding agent one acceptance test at a time, beginning with the vertical slice.
- Commit after each working stage and keep a known-good demo fixture.
- Never paste service-role keys, API keys, hateful raw datasets, or production secrets into prompts or browser code.
- Keep `ALLOW_THIRD_PARTY_CONTENT_INFERENCE=false` and `DEMO_DATA_MODE=synthetic` until an explicit authorization record is configured and tested.
- Use generated SQL migrations, then inspect them before applying. Keep RLS enabled and test anonymous denial.
- Prefer deterministic rules and explicit JSON schemas over elaborate agent chains.
- Freeze visual scope after the first polished dashboard; spend remaining time on the demo path and failure handling.

## 1. Decision summary

Use **Supabase/Postgres**, not MongoDB, as the system of record. Project Amanah’s core data is relational: content belongs to sources and runs; predictions belong to immutable model releases; reviews append to predictions; narratives and evidence have many-to-many/audit relationships; dashboards need grouped time queries. Postgres supplies constraints, transactions, joins, materialized views, JSONB for irregular source payloads, row-level security, and pgvector in one store. Supabase adds managed Auth, private Storage, migrations, and client libraries.

Keep a separate FastAPI layer even though Supabase exposes data APIs. The API centralizes disclosure rules, hides raw tables and service credentials, validates filters, generates safe aggregates, enforces review state transitions, rate-limits exports, and keeps classification/job orchestration independent of the frontend.

MongoDB becomes preferable only if the dominant requirement changes to high-volume, schema-fluid raw event archival with few joins and reviews. Even then, a practical split is object storage for raw payloads plus Postgres for normalized/queryable records; introducing MongoDB during the MVP creates another security, backup, and synchronization surface without clear benefit.

## 2. Service topology

```text
Browser
  │
  ├── Netlify: React/Vite static site
  │         │ Supabase Auth JWT
  │         ▼
  └── Render web service: FastAPI
            ├── Supabase Postgres / pgvector
            ├── Supabase private Storage
            └── queue (MVP: Postgres jobs; scale: Render Key Value/Celery)

Render cron or manual admin trigger
            │
            ▼
Render API process / bounded job
  collect → normalize → filter → infer → aggregate → signal/event jobs
```

For the hackathon, let the Render API run a bounded ingestion/classification operation invoked manually from an admin-only endpoint; add one [Render cron job](https://render.com/docs/cronjobs) only after the live path works. After the hackathon, move long-running work to a [Render background worker](https://render.com/docs/background-workers). Render filesystems are ephemeral, so evidence goes to object storage. Define backend infrastructure in a [Render Blueprint](https://render.com/docs/blueprint-spec).

GitHub Actions should run lint/tests/build checks and may execute the hackathon’s bounded incremental ETL directly. Netlify deploys the frontend and Render deploys the API from the Git repository. Actions is an ephemeral runner, never the data store: every stage checkpoints to Supabase and produces only a redacted run summary. Scheduled runs may be delayed, so provide manual dispatch and make every job idempotent. Move long-running or high-volume inference to a Render worker after the hackathon without changing the ETL command.

### Netlify frontend deployment

Official [Netlify Vite guidance](https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/) uses `npm run build` (or the equivalent package-manager command) and publishes `dist`.

For this monorepo, add `netlify.toml`:

```toml
[build]
  base = "apps/web"
  command = "pnpm build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

The SPA rewrite lets React Router handle direct navigation. Configure `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY` in Netlify. Anything prefixed with `VITE_` is bundled into browser JavaScript and must be considered public; never place the Supabase service-role key, database URL, hosted-model token, or trigger secret there. Netlify documents build-time [environment variable management](https://docs.netlify.com/build/environment-variables/get-started/).

## 3. Recommended technologies

- **Web:** React 19, Vite, TypeScript, React Router, TanStack Query, accessible chart library, Zod.
- **API:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, `psycopg`.
- **Workers:** same Python package; MVP Postgres job table + `FOR UPDATE SKIP LOCKED`; scale with Celery and Render Key Value.
- **ML:** PyTorch, Transformers, sentence-transformers, scikit-learn, ONNX Runtime where viable; EasyOCR/PaddleOCR or managed OCR after evaluation.
- **Database:** Supabase Postgres; `vector`, `pg_trgm`, and optionally Timescale only if supported/needed.
- **Storage/Auth:** private Supabase Storage buckets; Supabase Auth; short-lived signed URLs generated server-side.
- **Observability:** structured JSON logs with content redaction, Sentry/OpenTelemetry if approved, health/metrics endpoints.
- **Packaging:** `uv` for Python; `pnpm` for Node; Docker for API/worker reproducibility.

Pin exact versions in lockfiles at implementation time and run dependency/license/security checks. Do not hard-code model names throughout the application; use a model registry row and environment-configured active release.

## 4. Repository structure

```text
project-amanah/
├── apps/
│   └── web/                    # React/Vite marketing + dashboard
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   ├── src/amanah/
│   │   ├── api/                # FastAPI routes/auth
│   │   │   ├── communities.py  # registry/candidate decisions
│   │   │   └── reports.py      # immutable filtered report snapshots
│   │   ├── db/                 # sessions, repositories, migrations helpers
│   │   ├── schemas/            # canonical Pydantic contracts
│   │   ├── analysis/
│   │   │   ├── tools.py        # allowlisted read-only agent tools
│   │   │   ├── orchestrator.py # coverage gate → tools → validation
│   │   │   ├── prompts.py      # versioned server-owned instructions
│   │   │   └── validators.py   # citations, numbers, language, schema
│   │   ├── etl/
│   │       ├── __main__.py     # python -m amanah.etl
│   │       ├── cli.py          # stable CLI used locally/Actions/Render
│   │       ├── runner.py       # stage orchestration and checkpoints
│   │       ├── settings.py     # validated env/config
│   │       ├── run_report.py   # redacted JSON summary
│   │       ├── adapters/
│   │       │   ├── base.py
│   │       │   ├── youtube.py
│   │       │   ├── reddit.py   # conditional on approved access
│   │       │   ├── bluesky.py  # stretch
│   │       │   ├── x.py        # disabled until access/cost confirmed
│   │       │   ├── threads.py  # disabled until Meta permission confirmed
│   │       │   ├── tiktok.py   # disabled until Research API approval
│   │       │   ├── mastodon.py # instance-scoped stretch
│   │       │   └── fixtures.py
│   │       ├── stages/
│   │       │   ├── discover.py
│   │       │   ├── extract.py
│   │       │   ├── canonicalize.py
│   │       │   ├── normalize.py
│   │       │   ├── filter_candidates.py
│   │       │   ├── classify.py
│   │       │   ├── aggregate.py
│   │       │   ├── detect_signals.py
│   │       │   ├── discover_communities.py
│   │       │   ├── ingest_news.py
│   │       │   ├── rank_event_candidates.py
│   │       │   ├── forecast.py
│   │       │   └── generate_insights.py
│   │       └── repositories/   # runs/content/predictions/metrics upserts
│   │   └── reports/
│   │       ├── builder.py       # facts/charts/methodology assembly
│   │       ├── redaction.py
│   │       └── csv_export.py
│   └── tests/
│       ├── adapters/           # redacted source → canonical fixtures
│       ├── stages/
│       └── e2e/
├── config/
│   ├── lexicon.yml
│   ├── taxonomy.yml
│   ├── sources.example.yml     # safe committed template
│   ├── sources.production.yml  # IDs/queries only; no secrets
│   ├── communities.example.yml # source-scoped registry template
│   ├── news_sources.yml        # local/global scopes and feed allowlist
│   ├── data_policy.yml         # inference/transfer authorization rules
│   └── thresholds.yml
├── supabase/
│   ├── migrations/
│   ├── seed.sql                # synthetic demo data only
│   └── tests/                  # RLS and database tests
├── models/                     # manifests only; no large/restricted weights
├── docs/
│   ├── architecture/
│   ├── data-cards/
│   ├── model-cards/
│   ├── threat-model.md
│   └── runbook.md
├── fixtures/                   # synthetic/redacted API fixtures
├── scripts/
│   ├── validate_etl_config.py
│   ├── seed_demo.py
│   ├── verify_db_schema.py
│   ├── export_redacted_run.py
│   └── validate_report_snapshot.py
├── .github/workflows/
│   ├── ci.yml
│   ├── etl.yml
│   ├── etl-backfill.yml
│   ├── security.yml
│   ├── model-eval.yml
│   └── agent-eval.yml
├── render.yaml
├── netlify.toml
├── docker-compose.yml          # local services only
├── .env.example
├── SECURITY.md
└── README.md
```

## 5. Environment variables

Commit only `.env.example`. Separate browser-safe values from server secrets.

```dotenv
# Frontend (public by design)
VITE_API_BASE_URL=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=

# API/server
APP_ENV=development
APP_BASE_URL=http://localhost:8000
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET_RAW=amanah-raw-private
SUPABASE_STORAGE_BUCKET_DERIVED=amanah-derived-private
FIELD_ENCRYPTION_KEY=
AUTHOR_HMAC_KEY=
JOB_TRIGGER_SECRET=
CORS_ALLOWED_ORIGINS=http://localhost:5173
DEMO_DATA_MODE=synthetic
ALLOW_THIRD_PARTY_CONTENT_INFERENCE=false
THIRD_PARTY_TRANSFER_AUTHORIZATION_ID=

# Sources
YOUTUBE_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=project-amanah/0.1 contact@example.invalid
BLUESKY_JETSTREAM_URL=wss://jetstream2.us-east.bsky.network/subscribe
X_BEARER_TOKEN=                    # optional; access/cost must be approved
THREADS_ACCESS_TOKEN=              # optional; keyword-search permission required
TIKTOK_RESEARCH_CLIENT_KEY=        # optional; approved Research API only
TIKTOK_RESEARCH_CLIENT_SECRET=     # optional; approved Research API only
MASTODON_BASE_URL=                 # optional; named instance only
MASTODON_ACCESS_TOKEN=             # optional; depends on instance/search mode
GDELT_DOC_API_URL=https://api.gdeltproject.org/api/v2/doc/doc
NEWS_API_KEY=                         # optional; GDELT is enough for MVP
NEWS_API_BASE_URL=https://newsapi.org/v2

# Models
HF_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=
TEXT_RELEVANCE_MODEL_ID=
TEXT_HATE_MODEL_ID=Hate-speech-CNERG/bert-base-uncased-hatexplain
MULTIMODAL_MODEL_ID=
EMBEDDING_MODEL_ID=
MODEL_CACHE_DIR=/opt/models
INFERENCE_DEVICE=cpu

# Operations
LOG_LEVEL=INFO
RAW_RETENTION_DAYS=30
DERIVED_RETENTION_DAYS=180
MAX_MEDIA_BYTES=10485760
REPORT_MAX_AGGREGATE_ROWS=10000
SENTRY_DSN=
```

The Supabase service-role key, database URL, field-encryption key, HMAC key, source credentials, hosted-model key, authorization reference and trigger secret are server-only. Rotate on exposure. Prefer Render secret environment groups and GitHub encrypted environments; never print secrets or raw content in CI logs. A non-empty authorization ID does not itself enable transfer: the API must resolve an active authorization record whose data class, provider and purpose cover the request.

## 6. Database and storage implementation

Create migrations for enums/reference tables, core tables, indexes, RLS, views, functions, and retention jobs. Enable [`pgvector`](https://supabase.com/docs/guides/ai/vector-columns) for embeddings. Supabase/Postgres row-level security can govern vector-backed access too; see [RAG with permissions](https://supabase.com/docs/guides/ai/rag-with-permissions).

Recommended database roles:

- `anon`: no raw access; optional curated aggregate views only.
- `authenticated_analyst`: safe aggregates and redacted item views.
- `reviewer`: review queue and time-limited evidence access.
- `admin`: source/model configuration through API only.
- server service role: held only by API/worker; bypass is tightly controlled and audited.

Use SQL views/functions to expose `content_item_safe` and aggregate metrics without raw identifiers. RLS tests must prove cross-organization denial and anonymous denial. Never let the browser query raw evidence tables directly, even if policies appear correct.

Private storage paths:

```text
raw/{source}/{yyyy}/{mm}/{content_uuid}/{sha256}.{ext}
derived/{content_uuid}/ocr.json
derived/{content_uuid}/thumbnail.webp
reports/{organization_uuid}/{report_uuid}/report.html
reports/{organization_uuid}/{report_uuid}/summary.csv
exports/{organization_uuid}/{export_uuid}.zip   # controlled evidence bundle only
```

Signed URLs expire in minutes. Validate MIME by magic bytes; cap file size/pixels; strip metadata from derivatives. Database deletion creates an object-deletion job and tombstone; backup expiration is documented separately.

## 7. API contract

Version all endpoints under `/v1`. Return cursor pagination, UTC ISO timestamps, request IDs, and structured errors. OpenAPI is the source for generated TypeScript types.

### Public/system

- `GET /healthz` — process liveness
- `GET /readyz` — database/model readiness, no secrets
- `GET /v1/methodology` — active taxonomy/model/coverage disclosures

### Dashboard

- `GET /v1/overview?from=&to=&sources=` — totals, rates, coverage, review status
- `GET /v1/trends?metric=&interval=&from=&to=&source=&narrative=`
- `GET /v1/signals?status=&severity=&cursor=`
- `GET /v1/signals/{id}` — supporting aggregates and approved event links
- `GET /v1/forecasts?metric=&horizon_days=&from=&to=&sources=` — deterministic result, interval, coverage and backtest metadata
- `POST /v1/analysis/spikes/{signal_id}` — bounded, cached event-association investigation
- `GET /v1/narratives?from=&to=&cursor=`
- `GET /v1/narratives/{id}/items?cursor=` — redacted, authorized results
- `GET /v1/meme-families?from=&to=&cursor=`
- `GET /v1/content/{id}` — role-aware item/context/predictions
- `GET /v1/search?q=&...` — authenticated full-text search with safe filters
- `GET /v1/search/suggestions?q=` — autocomplete from approved suggestion classes
- `GET /v1/insights?from=&to=&...` — cached Gemini trend brief with citations
- `POST /v1/assistant/query` — tool-grounded Ask Amanah response
- `GET /v1/communities?source=&status=` — approved registry and aggregate-only candidates
- `POST /v1/reports` — immutable report snapshot from validated platform/community/date filters
- `GET /v1/reports/{id}` — report, coverage, methodology and safe download links
- `GET /v1/reports/{id}/summary.csv` — aggregate CSV; no authors/raw text by default
- `GET /v1/connections` — cached, secret-free integration status

### Review

- `GET /v1/review/tasks?status=&priority=&cursor=`
- `POST /v1/review/tasks/{id}/claim`
- `POST /v1/review/tasks/{id}/decisions` — requires idempotency key
- `POST /v1/review/tasks/{id}/release`
- `GET /v1/review/tasks/{id}/history`

### Admin/jobs

- `POST /v1/admin/runs` — create a bounded run for selected source/window
- `GET /v1/admin/runs/{id}`
- `POST /v1/admin/models/{id}/activate` — two-person approval in production
- `POST /v1/admin/community-candidates/{id}/decisions` — approve/dismiss/needs-context; idempotent and audited
- `POST /v1/internal/jobs/dispatch` — HMAC/OIDC protected, not browser-accessible
- `POST /v1/internal/retention/run`

### Evidence

- `POST /v1/evidence/{content_id}/access` — short-lived signed URL after authorization and audit
- `POST /v1/evidence/exports` — asynchronous, scoped bundle
- `GET /v1/evidence/exports/{id}`

Do not provide author search or bulk raw-content endpoints.

## 8. Job model and flows

`job(id, kind, payload, status, priority, run_after, attempts, max_attempts, locked_at, locked_by, idempotency_key, error_code)` supports retries and dead-letter state. Workers claim jobs transactionally with `FOR UPDATE SKIP LOCKED`. Each stage writes outputs before enqueueing the next stage.

### Daily ingestion

```text
schedule/dispatch
 → create collection_run (unique source + window)
 → collector pages by durable cursor
 → upsert source records
 → enqueue normalize per item
 → filter candidates
 → enforce data class + transfer/inference policy
 → local inference, authorized hosted inference, fixture result or policy skip
 → enqueue embedding/narrative membership
 → refresh metric buckets
 → detect signals
 → query GDELT/optional news event candidates
 → rank possible event associations
 → calculate and store deterministic forecast
 → generate/cache validated Gemini brief
 → close run with coverage statistics
```

### Community discovery

```text
bounded approved source discovery
 → aggregate candidate container IDs (subreddit/channel/feed/instance cohort)
 → require distinct-thread/minimum-volume thresholds
 → create community_candidate with reason and coverage
 → analyst approves, dismisses or requests context
 → approved candidate creates/updates community_registry
 → future runs may monitor it within explicit dates/query limits
```

No step searches people, joins identities across platforms, or labels the whole container hateful. The scheduled ETL never auto-approves a candidate.

### Media flow

```text
authorized URL
 → SSRF-safe fetcher + byte/pixel/type limits
 → SHA-256 exact dedupe
 → private object storage
 → pHash + safe derivative + OCR
 → visual relevance
 → data-policy gate
 → local/authorized multimodal inference, fixture result or policy skip reason
 → meme-family candidate
 → review if thresholds/disagreement require
```

### Report flow

```text
authorized analyst + validated filters
 → resolve exact data/model/methodology versions
 → freeze coverage, aggregates and citation IDs
 → apply redaction policy
 → create immutable report_snapshot
 → render accessible HTML + aggregate CSV
 → issue short-lived signed URLs
 → audit generation and download
```

For the hackathon, the frontend may render the stored JSON snapshot with print CSS so the browser saves it as PDF. Do not generate a mutable report directly from live queries at download time.

### Review flow

```text
prediction → priority rules → review_task
 → reviewer claims with lease
 → context/evidence access audited
 → append review_event
 → update effective-label view
 → metrics refresh
 → training-candidate pool (quarantined; never auto-train)
```

### Retention/deletion

```text
expired/source-deleted item
 → tombstone and hide
 → delete private objects/derived embeddings as policy requires
 → purge or irreversibly aggregate text
 → record audit outcome
 → allow backups to expire per documented window
```

## 9. GitHub Actions workflows

### 9.1 Stable ETL command

GitHub Actions, local development and a future Render worker must execute the same CLI. Workflow YAML orchestrates the environment; it does not contain ETL business logic.

```text
uv run --project backend python -m amanah.etl validate-config
uv run --project backend python -m amanah.etl run-from-env
uv run --project backend python -m amanah.etl resume --run-id <uuid>
uv run --project backend python -m amanah.etl status --run-id <uuid>
uv run --project backend python -m amanah.etl backfill-from-env
uv run --project backend python -m amanah.etl seed-fixtures
```

`run-from-env` reads validated environment inputs, creates `collection_run`, executes stages in order and writes a redacted `work/etl-run-summary.json`. Each stage upserts/checkpoints to Supabase before the next starts.

Expose the same CLI through `backend/pyproject.toml` for convenient local use:

```toml
[project.scripts]
amanah-etl = "amanah.etl.cli:app"
```

The incremental command reads the last successful cursor/window for each configured source query from Supabase. Workflow YAML must not calculate source cursors.

### 9.2 ETL stages and idempotency

```text
1. discover         query source or resolve seed IDs
2. extract          fetch bounded source payloads
3. canonicalize     map source fields → canonical ContentItem
4. normalize        create versioned normalized/model text
5. filter           apply relevance lexicon/model
6. authorize-input  enforce data class, provider-transfer and inference policy
7. classify         local, explicitly authorized hosted, fixture or policy-skip result
8. aggregate        refresh affected daily/community metrics
9. detect-signals   rolling-baseline spikes and narrative shifts
10. communities     optional aggregate candidates; never auto-approve
11. ingest-news     bounded local/global GDELT/optional NewsAPI queries
12. rank-events     transparent temporal/semantic candidate ranking
13. forecast        deterministic short-horizon forecast or abstention
14. insights        optional cached Gemini brief over allowed fact bundle
15. finalize        coverage counts, warnings and redacted run report
```

Required idempotency keys:

- collection run: `(source_query_id, window_start, window_end, mode)`
- content: `(source, source_item_id)`
- normalization: `(content_item_id, normalization_version)`
- prediction: `(content_item_id, model_release_id)`
- aggregate: `(metric_key, source, interval, bucket_start, filter_version)`
- news result: `(provider, canonical_url, published_at)` plus provider observation provenance
- forecast: `(metric, filter_hash, generated_bucket, horizon, model_version)`
- insight: `(filter_hash, data_version, model, prompt_version)`
- community candidate: `(source, source_community_id, discovery_window, discovery_config_version)`
- report snapshot: `(requested_by, filter_hash, data_version, methodology_version, redaction_mode)`

A retry must update/resume these records, never create duplicates. API rate limits and transient failures retry with bounded exponential backoff and jitter. Invalid credentials/configuration fail immediately. One bad item enters an item-level error/dead-letter record; it should not discard the complete run unless the failure rate crosses a configured threshold.

### 9.3 Runtime inputs

GitHub **environment secrets** in `etl-production`:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL                    # only if direct Postgres is required
YOUTUBE_API_KEY
GEMINI_API_KEY
AUTHOR_HMAC_KEY
FIELD_ENCRYPTION_KEY            # only if ETL writes encrypted fields
REDDIT_CLIENT_ID                # optional
REDDIT_CLIENT_SECRET            # optional
NEWS_API_KEY                    # optional; omit when using GDELT only
X_BEARER_TOKEN                  # optional; only when X adapter is approved/enabled
THREADS_ACCESS_TOKEN            # optional; only with keyword-search permission
TIKTOK_RESEARCH_CLIENT_KEY      # optional; approved research access only
TIKTOK_RESEARCH_CLIENT_SECRET   # optional; approved research access only
MASTODON_ACCESS_TOKEN           # optional; only if selected instance requires it
```

GitHub environment/repository **variables** (not secrets):

```text
ETL_CONFIG_PATH=config/sources.production.yml
ETL_DEFAULT_SOURCE=youtube
ETL_DEFAULT_QUERY_ID=all
ETL_MAX_ITEMS=1000
ETL_LOG_LEVEL=INFO
GEMINI_MODEL=<approved model configured at build time>
TEXT_MODEL_VERSION=<registered release>
NORMALIZATION_VERSION=v1
DEMO_DATA_MODE=synthetic
ALLOW_THIRD_PARTY_CONTENT_INFERENCE=false
```

`REDDIT_USER_AGENT` and `MASTODON_BASE_URL` may be variables if they contain no secret. Do not create or inject optional connector secrets until that adapter is approved and enabled. Secrets are explicitly injected only into the ETL job and never into PR workflows. Grant `GITHUB_TOKEN` only `contents: read`. Environment protection may require approval for backfills; routine bounded incremental runs can use the same environment without approval if the repository’s risk model permits.

### 9.4 `.github/workflows/etl.yml` — scheduled and manual incremental ETL

```yaml
name: Amanah ETL

on:
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:
    inputs:
      source:
        description: Source adapter
        required: true
        default: youtube
        type: choice
        options: [youtube, fixtures]
      query_id:
        description: Configured query ID or all
        required: true
        default: all
        type: string
      max_items:
        description: Hard item cap
        required: true
        default: "1000"
        type: string
      dry_run:
        description: Validate/discover without persistent content writes
        required: true
        default: false
        type: boolean

permissions:
  contents: read

concurrency:
  group: amanah-etl-production
  cancel-in-progress: false

jobs:
  etl:
    runs-on: ubuntu-latest
    timeout-minutes: 40
    environment: etl-production
    env:
      APP_ENV: production
      ETL_CONFIG_PATH: ${{ vars.ETL_CONFIG_PATH }}
      ETL_SOURCE: ${{ inputs.source || vars.ETL_DEFAULT_SOURCE }}
      ETL_QUERY_ID: ${{ inputs.query_id || vars.ETL_DEFAULT_QUERY_ID }}
      ETL_MAX_ITEMS: ${{ inputs.max_items || vars.ETL_MAX_ITEMS }}
      ETL_DRY_RUN: ${{ inputs.dry_run || false }}
      ETL_LOG_LEVEL: ${{ vars.ETL_LOG_LEVEL }}
      DEMO_DATA_MODE: ${{ vars.DEMO_DATA_MODE }}
      ALLOW_THIRD_PARTY_CONTENT_INFERENCE: ${{ vars.ALLOW_THIRD_PARTY_CONTENT_INFERENCE }}
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
      YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      NEWS_API_KEY: ${{ secrets.NEWS_API_KEY }}
      GEMINI_MODEL: ${{ vars.GEMINI_MODEL }}
      AUTHOR_HMAC_KEY: ${{ secrets.AUTHOR_HMAC_KEY }}
      NORMALIZATION_VERSION: ${{ vars.NORMALIZATION_VERSION }}
      TEXT_MODEL_VERSION: ${{ vars.TEXT_MODEL_VERSION }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v9
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock

      - name: Install locked ETL environment
        run: uv sync --locked --project backend --group etl

      - name: Validate configuration and database schema
        run: uv run --project backend python -m amanah.etl validate-config

      - name: Run incremental ETL
        run: uv run --project backend python -m amanah.etl run-from-env

      - name: Upload redacted run report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: etl-run-report-${{ github.run_id }}
          path: work/etl-run-summary.json
          if-no-files-found: ignore
          retention-days: 7
```

The scheduled run uses repository/environment variables because `workflow_dispatch` inputs are empty on a schedule. Use a non-round cron minute and do not promise exact execution time. The `fixtures` option is intentionally available for demo/recovery; it must label all inserted rows as fixture data.

### 9.5 `.github/workflows/etl-backfill.yml` — protected manual backfill

Manual only. Inputs: source, query ID, inclusive start date, exclusive end date, hard item cap, dry-run and a required confirmation string. Validate RFC 3339/ISO dates and refuse a window larger than 31 days or item cap above the configured maximum. Use a dedicated `etl-backfill` concurrency group and a protected `etl-production` environment with required reviewer if available. Run `python -m amanah.etl backfill-from-env` and upload only the redacted run report.

Never schedule a backfill, combine it with routine incremental runs or permit arbitrary source URLs in workflow inputs. Seed IDs/queries come from reviewed configuration.

### 9.6 `.github/workflows/ci.yml` — no live secrets

Triggers: pull requests and pushes to `main`.

- install from `backend/uv.lock` and the frontend lockfile;
- lint, format and type-check Python/TypeScript;
- run unit tests and source-adapter fixture contract tests;
- validate `sources.example.yml`, lexicon and taxonomy schemas;
- run `seed-fixtures` and the complete ETL against synthetic/redacted fixtures only;
- test that disallowed real-content data classes cannot invoke hosted inference;
- test that community candidates cannot become active without an authenticated append-only decision;
- validate report snapshots/CSV contain their filters, coverage, methodology and no author/raw-content fields;
- apply migrations to disposable Postgres/Supabase and test RLS;
- build the Netlify frontend and Render API image;
- ensure no known raw evidence, model weights or secrets were committed.

CI must never call YouTube, Reddit, Gemini, GDELT or production Supabase. Secrets are not available to forked PRs and the test suite must not depend on them.

### 9.7 `.github/workflows/model-eval.yml`

Manual plus changes to approved model manifests/evaluation code. Fetch only approved/licensed evaluation data from controlled storage; verify hashes/dataset cards; run the frozen holdout, benign-Muslim false-positive slice and calibration checks; produce a redacted metrics/model-card artifact. Do not activate a new release automatically.

### 9.8 `.github/workflows/security.yml`

Weekly and pull requests: dependency review, secret scan, container/dependency vulnerabilities, action pinning/static workflow analysis, migration/RLS checks, SBOM/license report and forbidden-file scan. Treat third-party actions as dependencies; pin immutable commit SHAs after the hackathon.

### 9.9 `.github/workflows/agent-eval.yml`

Run on changes to `backend/src/amanah/analysis/**`, forecast code, prompt/schema files or tool contracts, and allow manual dispatch. Use only synthetic/redacted fixtures and mocked Gemini/news responses; never production content or secrets. The workflow must verify:

- every cited metric/item/news ID exists in the supplied fact bundle;
- generated numeric claims exactly match tool outputs;
- low coverage and too-short history produce an explicit abstention;
- forecast direction/range match the stored deterministic forecast;
- event language says `coincided with`, `associated with` or `possible explanation`, never `caused`;
- prompt-injection strings inside comments/OCR/news snippets cannot add tools or alter instructions;
- third-party inference requests are rejected for disallowed data classes even when prompt text asks to proceed;
- community-discovery tools cannot approve candidates or retrieve member/profile histories;
- report tools preserve the caller’s authorized filters and never return raw bulk content;
- unauthorized tools, arbitrary SQL/URLs and author/identity requests are refused;
- tool count, result count and date-window limits are enforced;
- the output validates against the versioned Pydantic/JSON Schema.

Store a small redacted test report as an artifact. Failing this workflow blocks prompt/tool-contract changes but never activates or deploys a model automatically.

### 9.10 Run report and logging contract

The artifact may contain:

```json
{
  "run_id": "uuid",
  "source": "youtube",
  "query_id": "all",
  "started_at": "...",
  "completed_at": "...",
  "status": "success",
  "counts": {
    "discovered": 50,
    "extracted": 42,
    "canonicalized": 42,
    "candidates": 18,
    "classified": 18,
    "failed": 0
  },
  "coverage_warnings": [],
  "safe_error_codes": []
}
```

Never include raw comments, OCR text, author identifiers, canonical URLs with private tokens, source payloads, prompts, API responses or secrets in logs/artifacts. Log internal UUIDs and safe error codes. GitHub artifacts are not evidence storage.

### 9.11 Deployment and later migration

Netlify and Render continue to deploy through provider Git integration; do not duplicate deployment inside ETL workflows. If Actions approaches timeout, memory or cost limits, change the workflow’s ETL step to call an authenticated Render dispatch endpoint. Render then runs the exact same `python -m amanah.etl run-from-env` command. Supabase checkpoints and idempotency keys make this migration operational rather than architectural.

### 9.12 Helper scripts

Keep scripts thin; they import the backend package and contain no collector/classifier logic:

- `scripts/validate_etl_config.py` — validate source configuration, required environment-variable names, query IDs, caps and schedule-safe settings without contacting providers.
- `scripts/verify_db_schema.py` — confirm required migrations, extensions, canonical schema version and ETL database permissions; read-only unless an explicit migration command is used elsewhere.
- `scripts/seed_demo.py` — load synthetic/redacted fixture data through the canonical adapter/ETL path and mark every record `is_fixture=true`.
- `scripts/export_redacted_run.py` — create the safe run-summary artifact from a `collection_run` UUID; never export content rows.

All operational commands return nonzero on validation/run failure. The runner records failure state in Supabase before exiting when possible. Scripts must not catch exceptions merely to make Actions appear successful.

### 9.13 Source configuration contract

`config/sources.production.yml` contains identifiers, queries and caps—not credentials:

```yaml
schema_version: 1

sources:
  youtube:
    enabled: true
    adapter_version: v1
    queries:
      - id: yt-broad-muslim-context-en-ca
        enabled: true
        query_purpose: broad_relevance
        sampling_stratum: ordinary_monitoring
        query: 'Muslim|Islam'
        order: date
        region_code: CA
        relevance_language: en
        lookback_hours: 24
        max_discovered: 10
        max_comments_per_video: 100
      - id: yt-demo-seeds
        enabled: true
        query_purpose: controlled_seed
        sampling_stratum: demo_fixture
        seed_video_ids: []
        max_comments_per_video: 100

  fixtures:
    enabled: true
    adapter_version: v1
    path: fixtures/etl/demo-source-payloads.json
```

`config/communities.example.yml` keeps container decisions separate from keyword queries:

```yaml
schema_version: 1
communities:
  - id: yt-approved-channel-cohort
    source: youtube
    source_community_ids: []
    community_type: channel_cohort
    name: Approved demo channel cohort
    inclusion_rationale: Controlled hackathon demonstration
    sampling_stratum: demo_fixture
    approval_status: active
    active_from: '2026-08-22T00:00:00Z'
    active_until: '2026-08-25T00:00:00Z'
```

`config/data_policy.yml` makes the third-party boundary executable:

```yaml
schema_version: 1
default:
  allow_third_party_content_inference: false
hosted_allowed_data_classes:
  - synthetic
  - redacted
  - controlled_authorized
require_transfer_authorization_for:
  - real_harmful_content
  - personal_data
```

Validate all configuration against Pydantic/JSON Schema before accessing Supabase or external APIs. A query/community/policy configuration change increments its version; historical runs retain the version used. Do not accept regex code, arbitrary Python, credentials or unrestricted URLs from workflow inputs.

Official references: [workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run), [concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency), [GitHub secrets](https://docs.github.com/en/actions/concepts/security/secrets), [secure use](https://docs.github.com/en/actions/reference/security/secure-use), and [uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/).

## 10. Render configuration

Define for the hackathon:

- `amanah-api`: Docker web service, `/healthz`, at least two instances for production if budget permits.
- `amanah-scheduler`: optional cron only after manual ingestion works.

Netlify owns `amanah-web`. Add `amanah-worker` and a queue after the hackathon, not during the first vertical slice.

Set API/worker deploys to run Alembic migrations as a pre-deploy command where supported. Make migrations backward-compatible: expand schema, deploy compatible code, backfill, then contract later. Handle `SIGTERM` by stopping new claims and returning active jobs to retry-safe state. Model downloads must happen at image build or startup into an appropriate cache; never rely on ephemeral writes surviving deploys.

## 11. Local development

Prerequisites: Docker, Node, Python, Supabase CLI (optional), YouTube key for live collection. Default development uses synthetic fixtures and local Postgres/Supabase. Provide commands through a `Makefile` or task runner:

```text
make setup       # install locked dependencies
make dev         # web + api + worker
make db-reset    # local-only database migration/seed
make test        # all safe tests
make e2e         # synthetic vertical flow
make eval-small  # redistributable smoke evaluation
```

Seeds contain no scraped hate or personal data. Developers explicitly opt in to restricted datasets and acknowledge content exposure.

## 12. Observability and operations

Track:

- collection latency, API quota, page/cursor progress, source errors
- observed/candidate/classified/skipped counts by stage
- source connection state (`connected`, `access_required`, `institutional_approval_required`, `fixture_only`, `disabled`) and last safe check
- data-policy blocks by class/provider without logging the underlying content
- community candidates created/approved/dismissed and registry review dates
- queue depth/age, retries, dead letters, stage duration
- model score distribution, abstention, disagreement, calibration drift
- review queue age and reviewer exposure workload (privacy-preserving)
- aggregate query latency, storage growth, deletion completion
- report generation/download counts, filter hashes, redaction modes and failures
- coverage score per source/time bucket

Alert on stale source cursor, zero-volume anomaly, quota exhaustion, dead-letter growth, model-load failure, retention failure, and RLS/auth errors. Logs contain IDs and error codes, not raw text, author handles, URLs with tokens, OCR, or model prompts.

Operational runbooks cover compromised secret, harmful-content leak, source terms change, deletion request, model rollback, collector outage, corrupt evidence hash, and reviewer safety incident.

## 13. Testing strategy

- **Unit:** normalization invariants, lexicon tests, hash/dedupe, thresholds, spike math.
- **Contract:** recorded/redacted API fixtures for each source; schema evolution tests.
- **Database:** constraints, idempotency, migration forward/backward compatibility, RLS denial cases.
- **ML:** frozen holdout; per-class/source/language slices; calibration; counterfactual identity-term tests; meme family split.
- **Security:** XSS strings, hostile URLs, oversized/polyglot images, decompression bombs, prompt injection, signed-URL expiry.
- **End-to-end:** synthetic post and meme through collection to reviewed dashboard metric.
- **Resilience:** retries, duplicate delivery, partial pages, source deletion, quota failure, worker termination.

## 14. Staged implementation plan

### Hours 0–4 — skeleton and demo contract

Freeze a small taxonomy, draw the five demo screens, prepare a synthetic fixture, scaffold the monorepo, and create the Supabase tables/RLS.

**Exit:** CI passes; anonymous/raw access is denied; a synthetic item can be stored and audited.

### Hours 4–14 — vertical text slice

Implement controlled YouTube/fixture ingestion, normalization, a small lexicon, local classifier or policy-gated hosted wrapper, Supabase writes, FastAPI overview/item endpoints, and the first Netlify deployment.

**Exit:** one permitted synthetic/redacted/controlled comment travels end to end idempotently; dashboard shows denominator, model version, data class and inference location; an unauthorized hosted transfer is rejected.

### Hours 14–24 — dashboard and review

Polish overview/trend/narrative views; add chart drill-down, content warning, item context, confirm/reject review, and minimal audit history. Seed a coherent dataset so every screen tells the same story.

**Exit:** reviewer correction changes effective aggregate without overwriting original prediction; evidence access is audited.

### Hours 24–32 — spike, event, forecast, and meme story

Add a simple rolling-baseline spike, one cached GDELT/news association, an experimental one- to three-day deterministic forecast with an insufficient-data path, and three precomputed multimodal examples. Generate one cached Gemini commentary from validated facts. Label prepared/cached results honestly.

**Exit:** simulated spike appears with explicit non-causal event language; the forecast shows a range/model version or abstains; both survive a missing-data test.

### Hours 32–40 — integration and failure paths

Test the exact demo route. Add loading, empty, API-failure, source-access-required and fixture-fallback states. If P0 is stable, add the immutable print-report/aggregate CSV. Check mobile layout, accessibility, content hiding, CORS, and secrets.

**Exit:** the complete demo path works from a clean browser, and hosted-API failure switches cleanly to labeled fixture data.

### Hours 40–48 — freeze and rehearse

Stop features. Fix only demo-blocking defects, record a backup demonstration with accurate captions/transcript, rehearse a 3–5 minute narrative, finalize tools/datasets/licenses/earlier-work disclosure, and verify Netlify/Render/Supabase from a clean browser.

**Exit:** the deployed demo works twice in succession and the fixture fallback works with external APIs unavailable.

## 15. First build backlog

1. Approve taxonomy and definition of anti-Muslim hate with domain reviewers.
2. Create Supabase project, private buckets, migrations, roles, and RLS tests.
3. Implement canonical `ContentItem` and YouTube adapter using [official comments documentation](https://developers.google.com/youtube/v3/docs/commentThreads/list).
4. Implement `lexicon.yml` compiler with positive, negative, and Unicode tests.
5. Wrap baseline models behind `RelevanceClassifier` and `HateClassifier` interfaces.
6. Add model release manifest and prediction idempotency.
7. Build overview/trend APIs and dashboard coverage strip.
8. Build review task/decision/audit flow.
9. Add approved community registry schema, source/query sampling strata and candidate non-auto-approval tests.
10. Add metrics/spike job, local/global GDELT event candidates and transparent association scoring.
11. Add deterministic forecast snapshots and cached, validated Gemini commentary over allowed fact bundles.
12. Add print-report snapshot/aggregate CSV if core flow is stable.
13. Add CI/security/agent-eval/deploy workflows and Render Blueprint.
14. Run the first frozen evaluation and publish its model/data cards.
15. Only then tune thresholds and add multimodal compute.

## 16. Launch checklist

- Source terms/access documented and owner assigned
- Data protection/ethics review completed for intended jurisdiction and users
- Demo uses synthetic/redacted/controlled content; third-party content transfer is denied by default and tested
- AI tools, datasets, outside materials, licenses and earlier work are disclosed
- Demonstration video has accurate captions or transcript
- Threat model and incident contacts current
- RLS, storage privacy, CORS, rate limits, signed URLs, and secret rotation tested
- Retention and deletion verified end to end
- Model cards show holdout and slice results; thresholds approved
- Public views contain no raw content or person-level search
- Content warnings, keyboard access, RTL, and redaction modes tested
- Coverage/missing-data warnings visible
- Backups, rollback, alerts, and runbooks exercised
- Demo fallback uses synthetic/redacted fixtures
- Conditional connectors truthfully show access/approval/fixture state; no scraping fallback exists
- Report export preserves source/community/date filters, coverage, methodology and redaction state

## 17. Key references

- [Supabase vector columns](https://supabase.com/docs/guides/ai/vector-columns)
- [Supabase RAG with permissions / RLS](https://supabase.com/docs/guides/ai/rag-with-permissions)
- [Render deployment concepts](https://render.com/docs/deploys)
- [Render background workers](https://render.com/docs/background-workers)
- [Render cron jobs](https://render.com/docs/cronjobs)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Netlify Vite deployment](https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/)
- [Netlify environment variables](https://docs.netlify.com/build/environment-variables/get-started/)
- [YouTube video search](https://developers.google.com/youtube/v3/docs/search/list) and [comment threads](https://developers.google.com/youtube/v3/docs/commentThreads/list)
- [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms)
- [X post search](https://docs.x.com/x-api/posts/search/introduction)
- [Official Meta Threads keyword search](https://www.postman.com/meta/threads/request/m9j4i2x/search-for-threads-posts)
- [TikTok Research Tools](https://developers.tiktok.com/docs/en/about-research-api)
- [Mastodon search API](https://docs.joinmastodon.org/methods/search/)
- [GitHub Actions workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run)
- [YouTube comment threads API](https://developers.google.com/youtube/v3/docs/commentThreads/list)
- [Bluesky firehose/Jetstream](https://docs.bsky.app/docs/advanced-guides/firehose)
- [Reddit Data API guidance](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki)
