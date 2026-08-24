# Deploying and recovering the Amanah backend

Last reviewed: 2026-08-24

This runbook covers the Render API and GitHub Actions ETL defined by
`render.yaml` and `.github/workflows/etl.yml`. Netlify deploys the frontend
through its provider integration; the ETL workflow deploys neither service.

## Required environment handoff

Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, and any permitted
connector/encryption credentials as Render secrets, never in Git or browser
variables. Set `APP_ORIGIN` to the exact frontend HTTPS origin. Missing optional
connector keys leave only that connector disabled.

For live YouTube collection, add `YOUTUBE_API_KEY` to the GitHub
`etl-production` environment secrets. The browser and Netlify must never receive
this key. The reviewed runtime catalogue, not possession of the key, determines
which video IDs may run.

Set the same GitHub environment's non-secret variables to
`ETL_DEFAULT_SOURCE=youtube`, `ETL_CONFIG_VERSION=2026.08.24.1`, and
`ETL_MAX_ITEMS=500` before relying on the scheduled run. This is the aggregate
ceiling for five seeds that are each capped at 100 items. A manually dispatched
workflow still defaults to fixtures, so explicitly select `youtube` while
testing.

In Netlify, set `VITE_DATA_MODE=live`, `VITE_API_BASE_URL` to the Render HTTPS
origin, and the public Supabase project URL and anon key as
`VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY`. Every `VITE_*` value is public;
never hand Netlify the database URL, JWT secret, service-role key, provider key,
or encryption key. In Supabase, keep anonymous product access denied by RLS and
allow only the exact Netlify authentication callback/recovery origins.

The pre-deploy command applies Alembic migrations separately from application
startup. Review the generated SQL before the first production deploy.

## Deploy and smoke check

1. Validate and sync the Render Blueprint.
2. Wait for `/readyz` to return `200`; `/healthz` proves liveness only.
3. Set `AMANAH_SMOKE_BASE_URL` and a short-lived demo access token locally.
4. Run `uv run --project backend python -m amanah.observability.smoke`.

The smoke check proves health/readiness remain anonymous, product routes deny
anonymous access, and the demo account can read identity and dashboard data. It
performs no mutation and calls no provider.

## Manual ETL and fixture fallback

Use the **Amanah ETL** workflow. Seed keys must match the selected source and
exact reviewed config version. Datapack inputs are stable IDs from
`config/datapacks.example.yml`, never paths or URLs. Dry-run a new live source.

For the current YouTube demo catalogue:

1. Confirm the `etl-production` environment has `YOUTUBE_API_KEY` and the normal
   database/Supabase secrets.
2. Dispatch **Amanah ETL** with source `youtube`, config version
   `2026.08.24.1`, maximum items `500`, and dry run enabled. Leave registry keys
   blank to exercise the full five-video shortlist, or supply one stable key
   from `config/source-seeds.example.yml` for a smaller smoke test.
3. Inspect the redacted run-summary artifact. Unavailable videos, disabled
   comments, omitted replies, and quota exhaustion must appear as coverage
   warnings; they must not appear as zero activity or trigger scraping.
4. Repeat the dispatch with dry run disabled. The workflow synchronizes the
   reviewed configuration before collecting and then schedules analysis.
5. Verify the resulting dashboard coverage names YouTube, config version
   `2026.08.24.1`, and the applicable sampling stratum. Do not describe results
   from this deliberately enriched shortlist as YouTube-wide prevalence.

When provider access is unavailable for a demo, explicitly select `fixtures`.
Fixture mode remains labelled in run provenance and every item; it is never
silently substituted for failed live data.

## Rollback

1. Stop new manual dispatches and let the non-cancelling concurrency group finish.
2. Roll Render back to the last healthy artifact.
3. Do not downgrade the database automatically. Migrations follow
   expand/deploy/backfill/contract so the prior artifact remains compatible.
4. Run the smoke check and inspect safe error codes in redacted summaries.
5. Resume ETL only after confirming no overlapping active run.

## Missing keys and known limitations

- No database makes readiness degraded and product reads return `503`, never an
  empty result.
- No Gemini key defers AI while stored items and deterministic metrics remain.
- YouTube has a reviewed, preflighted five-video demo shortlist. Missing or
  invalid `YOUTUBE_API_KEY` disables the connector; quota, deleted videos, and
  disabled comments become typed coverage gaps. There is no scraping fallback.
  Reddit has no runnable adapter.
- The API's global IP ceiling is per instance; configure the same ceiling at the
  Render edge for multi-instance enforcement. Mutations also retain durable
  database-backed per-user limits.
- Redacted workflow artifacts are diagnostics, not evidence storage.

## Live/mock inventory

| Capability | Production state | Failure behavior |
|---|---|---|
| API/Postgres reads | Live when ready | `503`, never fixture substitution |
| Reviewed RSS | Live bounded metadata/excerpts | Last success plus coverage warning |
| YouTube | Live, bounded official API for five reviewed seeds when `YOUTUBE_API_KEY` is configured | Typed access/quota/coverage gap; no scraping fallback |
| Reddit | Disabled; no adapter | No scraping fallback |
| Gemini | Optional live connector | Typed deferral; deterministic metrics stay |
| Fixtures | Explicit fixture mode only | Every row/response remains labelled |
| Open datapacks | Allow-listed manifest IDs only | Fail-before-write on governance/hash/schema error |
