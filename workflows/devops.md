# 🚀 DevOps / Release Workflow

Self-contained playbook for shipping and operating: infrastructure-as-code, environments, CI/CD, observability, progressive deployment, rollback, and incident readiness. This is the track that takes green feature work to production and keeps it healthy.

**Rules in scope:** `rules/devops.md` (primary), `rules/security.md`, `rules/backend.md` (Deployment Readiness, Observability), `rules/documentation.md`
**Upstream sources:** `sources/Google_SRE_Workbook.md`, `sources/CNCF_Maturity_Model.md`, `sources/Twelve Factor App.md`, `sources/Microsoft_Engineering_Playbook.md`

> Prerequisite: complete the shared phases in [../Workflow.md](../Workflow.md). This track typically runs **in parallel** with feature tracks (set up CI/IaC early) and **gates the final release**.

---

## Build order

```
D0 IaC & environments ─► D1 CI/CD pipeline ─► D2 Observability ─► D3 Deploy & rollback
                                                                        │
                                                                        ▼
                                                  D4 SLOs & alerting ─► D5 Incident & DR readiness
```

---

## Step D0 — Infrastructure & Environments

**Checklist**
- [ ] All infra defined as code (Terraform/Pulumi/etc.), in version control, PR-reviewed
- [ ] Three environments: dev, staging, prod — same IaC modules, same images, config via env only
- [ ] Secrets in a manager (Vault/AWS/GCP/Azure), never in IaC repos
- [ ] Ephemeral preview environments per PR (created on open, torn down on merge)
- [ ] Service catalog entry: owner, SLO tier, upgrade status

### Prompt D0 — Infrastructure as code

```
You are defining infrastructure as code. Follow rules/devops.md (Infrastructure, Environments)
and Twelve-Factor.

Produce:
1. IaC modules for the service's backing resources (DB, cache, queue, object storage),
   parameterized so dev/staging/prod use the SAME modules with different inputs.
2. Environment matrix: what differs across dev/staging/prod (only runtime config should differ;
   base image + backing-service versions MUST match prod).
3. Secret injection from a secrets manager at runtime — NOT in the IaC repo, NOT in images,
   NOT in ConfigMaps. Show the wiring (e.g. Vault sidecar / mounted in-memory volume).
4. A non-secret config source (ConfigMap/env file) for things like LOG_LEVEL, feature flags.
5. A service-catalog entry: owner, SLO tier, shared-responsibility split.

Tech stack + cloud from spec: [PASTE relevant section]
Reference files: rules/devops.md, rules/security.md
```

---

## Step D1 — CI/CD Pipeline

### Prompt D1 — Pipeline

```
You are building the CI/CD pipeline. Follow rules/devops.md (CI/CD) and rules/agentic.md (CI gates).

Stages in strict order: lint → unit tests → integration tests → security scan → build artifact →
deploy staging → smoke tests → promote production.

Rules:
- Build artifact is IMMUTABLE; the same image/tag is promoted across environments (build/release/run
  separation). Tag every deploy with commit SHA + pipeline run ID + team.
- Target: staging deploy < 10 minutes.
- Dependency manifests committed and verified (reproducible builds).
- Production uses canary or blue/green — never direct full-fleet.
- Required gates that block merge: zero-warning lint, type check, unit + integration tests,
  secret detection, dependency/CVE scan, and a test-count guard (fails if test count drops).

Produce:
1. The pipeline config for the platform (GitHub Actions / GitLab CI / etc.).
2. A multi-stage Dockerfile: minimal final image, non-root user, no secrets baked in.
3. A smoke-test script run against staging post-deploy.

App + tech stack: [PASTE spec section]
Reference files: rules/devops.md, rules/security.md, rules/agentic.md
```

---

## Step D2 — Observability

### Prompt D2 — Metrics, logs, traces

```
You are instrumenting observability. Follow rules/devops.md (Monitoring/Logging/Metrics) and
rules/backend.md (Observability).

Produce:
1. The four golden signals per service: latency (p50/p95/p99), traffic (RPS), errors (5xx/timeouts),
   saturation (CPU/mem/queue depth) — exported in Prometheus format at /metrics.
2. Structured JSON logging contract: timestamp (ISO 8601 UTC), severity, service, version,
   trace_id, span_id, message; runtime-configurable verbosity; NO secrets/PII.
3. Distributed tracing: W3C traceparent propagated to all downstream calls; DB/cache/outbound
   HTTP each in a child span.
4. Prometheus recording rules that precompute the error ratio over 5m/1h/6h windows for SLO alerting.
5. A base dashboard template (golden signals) + per-service panels.

Metric naming: <namespace>_<subsystem>_<unit>_total (counters); histograms for latency; NO
high-cardinality labels (user/entity IDs).

Service(s): [DESCRIBE]
Reference files: rules/devops.md, rules/backend.md
```

---

## Step D3 — Deploy & Rollback

### Prompt D3 — Progressive deployment + rollback

```
You are defining the deployment + rollback strategy. Follow rules/devops.md (Deployments, Rollbacks)
and rules/backend.md (Deployment Readiness).

Produce:
1. A canary (or blue/green) rollout spec with SLO-gated promotion:
   promote only if canary_error_rate ≤ control * 1.1 AND canary_p99 ≤ control * 1.1.
2. Expand/contract migration ordering: backward-compatible schema change deploys BEFORE the app
   change; cleanup is a later migration. Never couple a breaking migration with an app deploy.
3. A SCRIPTED, version-controlled rollback that completes < 5 min for Tier-1 (e.g. helm rollback
   to the previous revision) + a verification command.
4. Graceful shutdown confirmation: SIGTERM → deregister → drain (bounded) → release locks → exit 0.
- Auto-halt + alert if the canary burns error budget faster than control.

Service + deploy platform: [DESCRIBE]
Reference files: rules/devops.md, rules/backend.md
```

---

## Step D4 — SLOs & Alerting

### Prompt D4 — SLOs + multi-burn-rate alerts

```
You are defining SLOs and alerting. Follow rules/devops.md (SLOs, Alerting).

Produce:
1. At least one SLO per service as SLI = good/total, with target + window + error budget
   (e.g. availability 99.9% / 30d → 43.2 min budget; latency: % served < 200ms).
2. An error-budget policy: what work halts at <50% budget and at <0% budget.
3. Multi-window, multi-burn-rate alerts (page on fast burn 14.4x/1h and 6x/6h; ticket on slow
   burn 1x). Each alert carries a runbook link, affected SLO, and current burn rate.
4. Alert hygiene: actionable-only (no paging on non-actionable); suppress child alerts when a
   dependency is down; target < 5 pages per on-call shift.

Service + reliability target: [DESCRIBE]
Reference files: rules/devops.md
```

---

## Step D5 — Incident & DR Readiness

### Prompt D5 — Runbooks, backups, DR

```
You are preparing incident-response and disaster-recovery readiness. Follow rules/devops.md
(Incident Response, Backups, Disaster Recovery).

Produce:
1. An incident-response runbook: declare early; single Incident Commander; #incidents channel;
   running timeline; mitigate before root-cause; status updates every 30 min; blameless
   postmortem within 5 business days for SEV-1/2 with tracked action items.
2. Severity definitions (SEV-1/2/3) with IC + postmortem requirements.
3. Automated backups meeting RPO (schedule, off-site/region, IAM-restricted, integrity-verified,
   restore tested monthly for Tier-1).
4. A DR plan with explicit RTO/RPO, failover runbook stored OUTSIDE prod access, and an annual
   drill checklist.

Service tier + RTO/RPO targets: [DESCRIBE]
Reference files: rules/devops.md
```

---

## Documentation gate (before GA)

```
You are finalizing release documentation. Follow rules/documentation.md.

Produce/verify:
1. README with a tested quick-start (clone → running), prerequisites, and links to architecture,
   API reference, runbooks, and the ADR log.
2. .env.example documenting EVERY variable (secrets as <REDACTED> with a vault pointer).
3. docs/architecture/ C4 context + container diagrams as committed Mermaid/PlantUML, with a
   "last reviewed" date.
4. CHANGELOG.md updated (Keep a Changelog format) for user-visible changes; deprecations note
   the removal version + Deprecation/Sunset headers.

Project: [PASTE spec section]   API: [PASTE openapi.yaml if any]
Reference files: rules/documentation.md
```

---

## Definition of Done (DevOps / Release)

- [ ] All infra is code, reviewed; dev/staging/prod share modules + images; config via env only
- [ ] Secrets injected at runtime from a manager; none in repos/images/logs
- [ ] CI runs lint → tests → security scan → build → staging → smoke → prod; immutable artifact promoted
- [ ] All required merge gates green (incl. secret detection, CVE scan, test-count guard)
- [ ] Golden-signal metrics, structured logs, and tracing live; dashboards exist
- [ ] Progressive rollout with SLO-gated promotion; scripted rollback tested (< 5 min Tier-1)
- [ ] Migrations follow expand/contract; graceful shutdown verified
- [ ] SLOs + error-budget policy + multi-burn-rate alerts defined and tested
- [ ] Backups automated + restore-tested; DR plan with RTO/RPO; incident runbook in place
- [ ] README quick-start tested; CHANGELOG + architecture docs current

→ Back to [../Workflow.md](../Workflow.md) for the next feature, or operate via the monitoring + incident runbooks above.
