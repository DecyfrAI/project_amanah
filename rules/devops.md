# DevOps Engineering Standards

> Grounded in the CNCF Platform Engineering Maturity Model, the Twelve-Factor App, and the Google SRE Workbook.

---

## Table of Contents

1. [Infrastructure](#infrastructure)
2. [Environments](#environments)
3. [CI/CD](#cicd)
4. [Deployments](#deployments)
5. [Rollbacks](#rollbacks)
6. [Monitoring](#monitoring)
7. [Alerting](#alerting)
8. [Logging](#logging)
9. [Metrics](#metrics)
10. [SLOs](#slos)
11. [Incident Response](#incident-response)
12. [Backups](#backups)
13. [Disaster Recovery](#disaster-recovery)

---

## Infrastructure

### Principles

- All infrastructure MUST be defined as code (IaC). Manual changes to production infrastructure are prohibited.
- Infrastructure code MUST be stored in version control, reviewed via pull request, and subject to the same CI pipeline as application code.
- Infrastructure MUST be reproducible: given the same inputs, applying the code twice MUST produce the same result (idempotency).
- Secrets and credentials MUST NOT be stored in IaC repositories. They MUST be injected at runtime from a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager).
- Infrastructure teams SHOULD publish a service catalog listing every managed capability, its owner, its SLO, and its upgrade status.
- Platform capabilities (databases, queues, object storage) SHOULD be provisioned via self-service APIs. Ticket-driven provisioning is an anti-pattern.
- A shared responsibility model MUST be documented: it defines what the platform team owns versus what the application team owns for every capability.

### Examples

```hcl
# Terraform module — reproducible RDS instance
module "app_db" {
  source        = "//platform/modules/rds"
  engine        = "postgres"
  engine_version = "15.4"
  instance_class = "db.t4g.medium"
  backup_retention_days = 7
  tags = {
    team    = "payments"
    env     = "production"
    slo_tier = "tier-1"
  }
}
```

```bash
# Self-service database provisioning via internal API
curl -X POST https://platform.internal/v1/databases \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"engine":"postgres","version":"15","team":"payments","env":"staging"}'
# Returns: { "host": "...", "secret_path": "vault/payments/db/staging" }
```

---

## Environments

### Principles

- Every service MUST run in at least three environments: **development**, **staging**, and **production**.
- All environments MUST be built from the same IaC modules and the same container images. Environment-specific variation MUST be limited to configuration injected at runtime (Twelve-Factor Factor III).
- Dev/prod parity MUST be maximized (Twelve-Factor Factor X). Differences in backing service versions, OS versions, or network topology between staging and production are a known source of incidents.
- Configuration MUST be stored in the environment, never in the codebase. Hardcoded hostnames, credentials, or feature toggles in source code are prohibited.
- Ephemeral preview environments SHOULD be created automatically for every pull request and torn down on merge.
- All environments SHOULD use the same monitoring, logging, and alerting stack. Silent environments hide bugs.

### Environment matrix

| Property              | Development        | Staging            | Production         |
|-----------------------|--------------------|--------------------|--------------------|
| IaC source            | Same modules       | Same modules       | Same modules       |
| Container image       | Branch build       | Same as prod build | Immutable tag      |
| Config source         | `.env` / Vault dev | Vault staging      | Vault prod         |
| Backing service ver.  | MUST match prod    | MUST match prod    | Canonical          |
| Monitoring            | SHOULD be active   | MUST be active     | MUST be active     |
| SLO enforcement       | MAY be relaxed     | SHOULD be active   | MUST be active     |

### Example

```yaml
# Kubernetes ConfigMap — only non-secret, non-credentials config lives here
apiVersion: v1
kind: ConfigMap
metadata:
  name: payment-service
  namespace: production
data:
  LOG_LEVEL: "info"
  FEATURE_NEW_CHECKOUT: "true"
  DB_MAX_CONNECTIONS: "50"
# Credentials come from a Vault sidecar, never from ConfigMap
```

---

## CI/CD

### Principles

- Every commit to a mainline branch MUST trigger a CI pipeline automatically. Manual deployments to staging or production without CI are prohibited.
- The pipeline MUST strictly separate the **build**, **release**, and **run** stages (Twelve-Factor Factor V). A build artifact (container image, binary) MUST be immutable once created; the same artifact is promoted across environments.
- The pipeline MUST run, in order: lint → unit tests → integration tests → security scan → build artifact → deploy to staging → smoke tests → promote to production.
- All pipeline configuration MUST be stored in version control alongside the application code.
- Pipeline execution time to staging SHOULD be under 10 minutes. Longer pipelines reduce developer feedback loops and increase batch size.
- Test coverage gates SHOULD be enforced in CI. A failing gate blocks promotion.
- Dependency manifests (e.g., `package-lock.json`, `go.sum`, `requirements.txt`) MUST be committed and verified in CI to ensure reproducible builds (Twelve-Factor Factor II).

### Example pipeline (GitHub Actions skeleton)

```yaml
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
      - run: make lint test
      - run: docker build -t registry/payments:${{ github.sha }} .
      - run: docker push registry/payments:${{ github.sha }}

  security-scan:
    needs: build
    steps:
      - run: trivy image registry/payments:${{ github.sha }}

  deploy-staging:
    needs: security-scan
    steps:
      - run: helm upgrade --install payments ./chart
          --set image.tag=${{ github.sha }}
          --namespace staging

  smoke-test:
    needs: deploy-staging
    steps:
      - run: ./scripts/smoke-test.sh https://staging.payments.internal

  deploy-production:
    needs: smoke-test
    if: github.ref == 'refs/heads/main'
    steps:
      - run: helm upgrade --install payments ./chart
          --set image.tag=${{ github.sha }}
          --namespace production
```

---

## Deployments

### Principles

- Deployments MUST be automated. Humans MUST NOT apply changes directly to production.
- Every deployment MUST produce a small, self-contained change set. Large "big bang" releases increase blast radius and complicate rollback.
- Production deployments MUST use a progressive rollout strategy: **canary** or **blue/green**. Direct full-fleet deployments are prohibited for user-facing services.
- A canary MUST expose the new version to a small subset of traffic (typically 1–5%) before full promotion. The canary population MUST be evaluated against SLO metrics before the rollout proceeds.
- Deployments SHOULD be gated on SLO burn rate. If the canary burns the error budget faster than the control, the deployment pipeline MUST halt and alert.
- Rollouts SHOULD happen during business hours. Weekend or holiday deployments SHOULD require explicit approval and elevated on-call coverage.
- Every deployment MUST be tagged with the commit SHA, pipeline run ID, and deploying team for auditability.

### Canary evaluation criteria

```
canary_error_rate = bad_requests_canary / total_requests_canary
control_error_rate = bad_requests_control / total_requests_control

# Promote if:
canary_error_rate <= control_error_rate * 1.1   # within 10% relative
canary_p99_latency_ms <= control_p99_latency_ms * 1.1
```

### Example — Argo Rollouts canary spec

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    canary:
      steps:
        - setWeight: 5
        - pause: { duration: 10m }
        - analysis:
            templates:
              - templateName: slo-check
        - setWeight: 50
        - pause: { duration: 10m }
        - setWeight: 100
      canaryMetadata:
        labels:
          role: canary
```

---

## Rollbacks

### Principles

- Every deployment MUST have a documented, tested rollback procedure before it is promoted to production.
- Rollback MUST be automated and MUST complete in under 5 minutes for Tier-1 services.
- Rollback procedures MUST be scripted and stored in version control. Undocumented manual rollback steps are prohibited.
- When an SLO burn rate alert fires during a deployment window, the on-call engineer MUST initiate a rollback unless a known safe explanation is available.
- Database schema migrations that are not backward-compatible MUST NOT be deployed simultaneously with application changes. Use an expand-contract pattern: deploy the schema change first (backward-compatible), deploy the application change, then clean up.
- Rollback drill SHOULD be conducted at least once per quarter per Tier-1 service to verify that the procedure works within the stated time window.

### Example

```bash
# Automated rollback via Helm — revert to the previous release revision
helm rollback payments 0 --namespace production --wait --timeout 5m

# Verify rollback succeeded
kubectl rollout status deployment/payments -n production
```

---

## Monitoring

### Principles

- Monitoring configuration MUST be treated as code: stored in version control, reviewed, and deployed via CI/CD.
- Every service MUST export metrics in a standard format (e.g., Prometheus `/metrics` endpoint). Custom scraping scripts that bypass the standard format are an anti-pattern.
- Monitoring MUST cover the four golden signals: **latency**, **traffic**, **errors**, and **saturation**.
- Monitoring data MUST be available in near-real time. Staleness above 4–5 minutes materially degrades incident response.
- Dashboards MUST be consistent across services. All services SHOULD share a common base dashboard template supplemented by service-specific panels.
- Different audiences need different views. A high-level SLO compliance dashboard SHOULD be maintained for leadership; detailed signal dashboards for on-call engineers.
- Monitoring SHOULD use loose coupling: alerts and dashboards SHOULD remain functional if a single monitored target is unavailable.
- Distributed tracing SHOULD be enabled for all inter-service calls on Tier-1 services to support root-cause analysis.

### Four golden signals definitions

| Signal      | What to measure                                              |
|-------------|--------------------------------------------------------------|
| Latency     | Time to serve a request; track p50, p95, p99 separately      |
| Traffic     | Requests per second; distinguish successful from failed      |
| Errors      | Rate of requests that fail (5xx, timeouts, explicit errors)  |
| Saturation  | How full the service is: CPU, memory, queue depth, disk I/O  |

### Example — Prometheus recording rules

```yaml
# Precompute error ratio for SLO alerting
- record: job:slo_errors_per_request:ratio_rate5m
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)
    /
    sum(rate(http_requests_total[5m])) by (job)

- record: job:slo_errors_per_request:ratio_rate1h
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[1h])) by (job)
    /
    sum(rate(http_requests_total[1h])) by (job)

- record: job:slo_errors_per_request:ratio_rate6h
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[6h])) by (job)
    /
    sum(rate(http_requests_total[6h])) by (job)
```

---

## Alerting

### Principles

- Alerts MUST be actionable. An alert that does not require a human to take action MUST NOT page a human.
- Alert configuration MUST be stored in version control alongside monitoring rules.
- Alerting MUST use a multi-window, multi-burn-rate strategy (see below). Simple threshold alerts on a short window produce too many false positives.
- Alert suppression MUST be configured to avoid alert storms: when a dependency is failing, child service alerts SHOULD be suppressed.
- Each alert MUST include a runbook link, the affected SLO, and the current burn rate.
- Paging alerts SHOULD target < 5 pages per on-call shift per week. Alert fatigue is an incident risk.
- Non-urgent alerts (slow burn) SHOULD create tickets, not pages.
- Alerting logic MUST be tested in CI. Untested alert rules are a reliability risk.

### Multi-window, multi-burn-rate alert tiers (for a 99.9% SLO over 30 days)

| Budget consumed | Window  | Burn rate | Action     |
|-----------------|---------|-----------|------------|
| 2% in 1 hour    | 1 hour  | 14.4      | **Page**   |
| 5% in 6 hours   | 6 hours | 6.0       | **Page**   |
| 10% in 3 days   | 3 days  | 1.0       | **Ticket** |

### Example — Prometheus alert rules

```yaml
groups:
  - name: slo.payments
    rules:
      - alert: PaymentsSLOFastBurn
        expr: |
          (
            job:slo_errors_per_request:ratio_rate1h{job="payments"} > (14.4 * 0.001)
          and
            job:slo_errors_per_request:ratio_rate5m{job="payments"} > (14.4 * 0.001)
          )
        labels:
          severity: page
          slo: payments-availability
        annotations:
          summary: "Payments burning error budget at 14x — 2% budget gone in 1h"
          runbook: "https://wiki.internal/runbooks/payments-slo-burn"

      - alert: PaymentsSLOSlowBurn
        expr: |
          (
            job:slo_errors_per_request:ratio_rate6h{job="payments"} > (6.0 * 0.001)
          and
            job:slo_errors_per_request:ratio_rate1h{job="payments"} > (6.0 * 0.001)
          )
        labels:
          severity: page
        annotations:
          summary: "Payments burning error budget at 6x — 5% budget gone in 6h"

      - alert: PaymentsSLOTicket
        expr: |
          job:slo_errors_per_request:ratio_rate6h{job="payments"} > (1.0 * 0.001)
        for: 1h
        labels:
          severity: ticket
        annotations:
          summary: "Payments slow burn — create ticket to investigate"
```

---

## Logging

### Principles

- Logs MUST be treated as event streams (Twelve-Factor Factor XI). Applications MUST write to stdout/stderr only; log routing, aggregation, and retention are the platform's responsibility.
- All logs MUST be structured (JSON). Unstructured text logs are prohibited in production because they cannot be reliably queried or alerted on.
- Every log line MUST include: `timestamp` (ISO 8601, UTC), `severity`, `service`, `version`, `trace_id`, `span_id`, and `message`.
- Log retention MUST be at least 30 days for production. Audit logs MUST be retained according to compliance requirements (typically 1–7 years).
- Applications MUST NOT log secrets, PII, or credentials. Log scrubbing MUST be enforced at the application layer, not relied upon downstream.
- Logs SHOULD be used for root-cause analysis; metrics SHOULD drive alerting. If an alert is based on a log query, the underlying signal SHOULD be exported as a metric counter instead.
- Log verbosity MUST be configurable at runtime without a restart (via environment variable or config reload).

### Example — structured log line

```json
{
  "timestamp": "2026-06-12T14:32:05.123Z",
  "severity": "ERROR",
  "service": "payments",
  "version": "a3f9c1d",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "charge failed: stripe returned 402",
  "user_id_hash": "sha256:e3b0c44...",
  "amount_cents": 4999,
  "currency": "USD",
  "error_code": "card_declined"
}
```

---

## Metrics

### Principles

- Metrics MUST be exported as monotonically incrementing counters where possible. Gauges are appropriate for values that can decrease (queue depth, in-flight requests).
- Metric names MUST follow a consistent naming convention: `<namespace>_<subsystem>_<unit>_total` for counters, `<namespace>_<subsystem>_<unit>` for gauges.
- Histograms MUST be used for latency and request size. Summary quantiles computed at the collection point SHOULD be avoided because they cannot be aggregated across instances.
- High-cardinality labels (user IDs, entity IDs, free-form strings) MUST NOT be used as metric labels. They cause memory exhaustion in the metrics backend.
- Every service MUST expose metrics for: request count, error count, latency histogram, and saturation (CPU/memory/queue).
- Platform-level metrics (node CPU, disk IOPS, pod restarts) MUST be collected by the platform team and made available to service teams.
- Metric data MUST be retained for at least 13 months to enable year-over-year capacity planning.

### Standard label set

```
job          – service name (e.g., "payments")
instance     – pod or host identifier
env          – "production" | "staging" | "development"
version      – image tag / git SHA
method       – HTTP method or RPC name
status       – HTTP status code or gRPC status
```

---

## SLOs

### Principles

- Every production service MUST have at least one SLO. A service without an SLO cannot be managed by objective.
- SLOs MUST be defined as a ratio of good events to total events (SLI = good / total). This format produces a value between 0% and 100% and directly yields an error budget.
- 100% is the wrong SLO target. Every additional nine of reliability costs exponentially more and delivers diminishing marginal value to users.
- SLOs MUST be agreed upon by all stakeholders (product, engineering, leadership) before they are enforced.
- Each SLO MUST have an **error budget policy** that specifies what engineering work is halted or prioritized when the error budget is exhausted.
- SLOs SHOULD be reviewed quarterly. If the service consistently exceeds its SLO, tighten it; if it consistently misses it, diagnose and fix the underlying reliability issues.
- SLO compliance reports MUST be published to all stakeholders on a regular cadence (weekly or monthly).

### SLI types by service type

| Service type    | SLI type     | Description                                                          |
|-----------------|--------------|----------------------------------------------------------------------|
| Request-driven  | Availability | Proportion of requests returning a successful response               |
| Request-driven  | Latency      | Proportion of requests served faster than a defined threshold        |
| Pipeline        | Freshness    | Proportion of data updated more recently than a time threshold       |
| Pipeline        | Correctness  | Proportion of records producing the expected output                  |
| Storage         | Durability   | Proportion of written records that can be successfully read          |

### Example SLO document (abbreviated)

```yaml
service: payments
slo:
  - name: availability
    description: "Proportion of HTTP requests that return non-5xx responses"
    sli:
      numerator: "sum(rate(http_requests_total{job='payments',status!~'5..'}[5m]))"
      denominator: "sum(rate(http_requests_total{job='payments'}[5m]))"
    target: 99.9%
    window: 30d
    error_budget: 0.1%   # 43.2 minutes of downtime per 30 days

  - name: latency
    description: "Proportion of requests served in < 200 ms (p99 gate)"
    sli:
      numerator: "http_request_duration_seconds_bucket{le='0.2',job='payments'}"
      denominator: "http_request_duration_seconds_count{job='payments'}"
    target: 99.0%
    window: 30d

error_budget_policy:
  - condition: "budget remaining < 50%"
    action: "Freeze non-critical feature work; SRE review required for all deployments"
  - condition: "budget remaining < 0%"
    action: "Freeze all deployments; escalate to engineering director"
```

---

## Incident Response

### Principles

- Incidents MUST be declared early. Waiting for full diagnosis before declaring an incident delays mobilization and worsens user impact.
- Every incident MUST have exactly one **Incident Commander (IC)** who owns coordination and communication. Incidents without a named IC are unmanaged incidents.
- The three Cs MUST be maintained throughout every incident: **Coordinate** response effort, **Communicate** status internally and externally, maintain **Control** of the response.
- A dedicated incident channel (Slack, Hangout, or equivalent) MUST be opened at declaration time. All incident-related communication MUST happen in that channel, not in side conversations.
- A running timeline of actions taken and their outcomes MUST be maintained during the incident. This record is the foundation of the postmortem.
- When an incident is mitigated, root cause MUST still be identified before the next deployment window. Mitigating without understanding the root cause risks recurrence.
- A blameless postmortem MUST be written and published within 5 business days of every Severity-1 or Severity-2 incident.
- Postmortem action items MUST be tracked to completion in the team's backlog. Orphaned action items are a leading indicator of repeated incidents.

### Severity definitions

| Severity | Criteria                                                         | IC required | Postmortem required |
|----------|------------------------------------------------------------------|-------------|---------------------|
| SEV-1    | SLO error budget > 5% consumed in < 1h; user-visible outage     | Yes         | Yes                 |
| SEV-2    | Partial degradation; error budget burning at elevated rate       | Yes         | Yes                 |
| SEV-3    | Non-user-visible issue; budget burn below ticket threshold       | No          | Optional            |

### Incident response checklist

```
□ Declare the incident; announce in #incidents channel
□ Assign Incident Commander (IC)
□ Assign Communications Lead (CL) for external updates if SEV-1
□ Open incident timeline doc (link in channel)
□ Identify current user impact and scope
□ Mitigate first — stop the bleeding before finding root cause
□ Update status page every 30 minutes while active
□ Post all-clear when user impact is resolved
□ Schedule postmortem within 24 hours
□ File postmortem action items in team backlog
```

---

## Backups

### Principles

- All stateful data MUST be backed up automatically on a defined schedule. Manual backups are not a substitute.
- Backup schedules MUST be defined based on Recovery Point Objective (RPO). A Tier-1 service with an RPO of 1 hour MUST back up at least hourly.
- Backups MUST be stored in a location physically separate from the primary data store (different availability zone at minimum; different region for Tier-1 services).
- Backup integrity MUST be verified automatically. A backup that has never been tested cannot be relied upon in a disaster.
- Backup restoration MUST be tested at least monthly for Tier-1 services, quarterly for Tier-2. Restoration tests MUST be automated and their results reported to the on-call team.
- Backup access MUST be restricted via IAM. Only the backup service account and incident responders with break-glass access SHOULD be able to read or delete backups.
- Backup retention MUST meet compliance requirements. For most production data, 30-day daily backups and 1-year monthly snapshots are a reasonable baseline.

### Example — automated backup schedule (Kubernetes CronJob)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: production
spec:
  schedule: "0 * * * *"    # every hour — satisfies RPO=1h
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: pg-dump
              image: registry/pg-backup:latest
              env:
                - name: S3_BUCKET
                  value: "backups-payments-prod-us-east-1"
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgres-creds
                      key: password
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump $PGDATABASE | gzip | \
                  aws s3 cp - s3://${S3_BUCKET}/$(date +%Y/%m/%d/%H%M%S).sql.gz
          restartPolicy: OnFailure
```

---

## Disaster Recovery

### Principles

- Every Tier-1 service MUST have a documented Disaster Recovery (DR) plan reviewed at least annually.
- DR plans MUST define **RTO** (Recovery Time Objective) and **RPO** (Recovery Point Objective) explicitly. Undefined RTOs result in uncoordinated recovery efforts.
- DR plans MUST be tested via drills at least once per year. Untested DR plans SHOULD be treated as non-existent.
- Runbooks for all failure modes (region failure, data corruption, credential loss) MUST be stored in a location accessible without production access (e.g., a separate docs system).
- Infrastructure for DR failover MUST be provisioned in advance via IaC and kept warm where the RTO requires it. Cold IaC-only recovery is acceptable only if the RTO allows for full provisioning time.
- Post-DR, a full incident postmortem MUST be conducted even if the DR drill was planned.
- Automation SHOULD handle failover for scenarios that occur frequently or that are time-critical. Human-driven failover for RTO < 15 minutes is unreliable.

### DR tiers

| Tier   | Example services             | RTO target | RPO target | Strategy                  |
|--------|------------------------------|-----------|-----------|---------------------------|
| Tier-1 | Payment processing, auth     | < 15 min  | < 5 min   | Active-active multi-region |
| Tier-2 | Reporting, notifications     | < 4 hours | < 1 hour  | Active-passive with warm standby |
| Tier-3 | Internal tooling, dashboards | < 24 hours | < 24 hours | IaC rebuild from backup    |

### DR drill checklist

```
□ Simulate failure scenario (region, database, key service)
□ Verify backups are accessible from DR region
□ Execute automated failover script
□ Validate service health via smoke tests
□ Confirm SLO metrics are reporting from DR region
□ Measure actual RTO against target — document delta
□ Update runbooks with lessons learned
□ File action items for gaps found
```
