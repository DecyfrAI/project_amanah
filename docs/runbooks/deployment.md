# Deploying and recovering the Amanah backend

Last reviewed: 2026-08-23

This runbook covers the Render API and GitHub Actions ETL defined by
`render.yaml` and `.github/workflows/etl.yml`. Netlify deploys the frontend
through its provider integration; the ETL workflow deploys neither service.

## Required environment handoff

Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, and any permitted
connector/encryption credentials as Render secrets, never in Git or browser
variables. Set `APP_ORIGIN` to the exact frontend HTTPS origin. Missing optional
connector keys leave only that connector disabled.

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

For the repository-owned demo datapack, set `ETL_DATAPACK_IDS` (or the manual
workflow's `datapack_ids` input) to `amanah-synthetic-demo-v1`. It is an approved
synthetic fixture under CC0-1.0, not an external live dataset. Its manifest hash
is verified before import, every imported row remains `is_fixture=true`, and
the `expected_*` columns remain dataset annotations rather than predictions.
First run the workflow with source `fixtures` and `dry_run=true`; after that
succeeds, repeat with `dry_run=false` to persist and analyze the 12 rows.

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
- YouTube remains disabled until reviewed approval and credentials exist. Reddit
  has no runnable adapter.
- The API's global IP ceiling is per instance; configure the same ceiling at the
  Render edge for multi-instance enforcement. Mutations also retain durable
  database-backed per-user limits.
- Redacted workflow artifacts are diagnostics, not evidence storage.

## Live/mock inventory

| Capability | Production state | Failure behavior |
|---|---|---|
| API/Postgres reads | Live when ready | `503`, never fixture substitution |
| Reviewed RSS | Live bounded metadata/excerpts | Last success plus coverage warning |
| YouTube | Access-required/disabled | No scraping fallback |
| Reddit | Disabled; no adapter | No scraping fallback |
| Gemini | Optional live connector | Typed deferral; deterministic metrics stay |
| Fixtures | Explicit fixture mode only | Every row/response remains labelled |
| Open datapacks | Allow-listed manifest IDs only | Fail-before-write on governance/hash/schema error |
