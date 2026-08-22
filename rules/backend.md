# Backend Engineering Rules

Distilled from the Microsoft Engineering Playbook, Thoughtbot guides, and the Twelve-Factor
App methodology. Applies to microservices, APIs, and background workers.

---

## Architecture

- Services MUST have a single, well-defined responsibility. A service owns its data store and
  exposes behavior through an explicit API boundary.
- Services MUST NOT share a database with another service. Cross-service reads MUST go
  through the owning service's API.
- Services SHOULD be independently deployable. A change to one service MUST NOT require
  coordinated deployment of another.
- Admin or maintenance tasks (migrations, data backfills, one-off scripts) MUST run as
  separate, one-off processes against the same release artifact — not baked into application
  startup.
- A service MUST be able to start and stop cleanly at any time. Startup MUST be fast (target
  under 10 seconds). Shutdown MUST drain in-flight requests and release locks before exiting.

---

## Service Boundaries

- Each service MUST own its own data — no shared tables, no shared queues consumed by
  multiple owners.
- Services SHOULD communicate via versioned, documented contracts (REST, gRPC, async
  events). Implicit coupling through shared libraries that encode domain logic MUST be
  avoided.
- Breaking changes to a public API MUST be versioned (e.g. `/v2/`) or negotiated via content
  negotiation before the old version is retired.
- Services SHOULD NOT call each other synchronously in a chain longer than two hops. Deep
  synchronous chains amplify latency and failure probability.

**Example — ownership boundary:**

```
# Correct: Order service calls Inventory service's API
GET /inventory/items/42/stock

# Incorrect: Order service queries Inventory's database directly
SELECT stock FROM inventory.items WHERE id = 42
```

---

## Configuration

- All configuration that varies between deploys (credentials, hostnames, feature flags,
  resource limits) MUST be stored in the environment, not in code.
- Configuration MUST NOT be committed to source control. Secrets MUST be injected at
  runtime via environment variables or a secrets manager.
- A service MUST start with a clear error when required configuration is missing, not silently
  degrade.
- Configuration SHOULD be validated at startup, not lazily at first use.

**Example — fail-fast on missing config:**

```python
DATABASE_URL = os.environ["DATABASE_URL"]   # KeyError on startup if absent
# Not: os.environ.get("DATABASE_URL")       # Silent None leads to a cryptic error later
```

---

## Environment Variables

- Environment variable names MUST be `UPPER_SNAKE_CASE`.
- Each variable MUST have a documented purpose and required/optional status in the
  project's configuration reference.
- A service MUST NOT read the same logical config value from multiple sources (env var AND
  config file AND default in code). Pick one authority per value.
- Secrets (passwords, API keys, tokens) MUST be provided as environment variables or
  fetched from a secrets manager at startup. They MUST NOT appear in logs, stack traces, or
  error responses.
- Services SHOULD ship a `.env.example` (or equivalent) listing every variable with a
  non-sensitive placeholder value so new environments can be bootstrapped without
  archaeology.

**Example — documented variable inventory:**

```
# .env.example
DATABASE_URL=postgres://user:pass@localhost:5432/mydb   # required
REDIS_URL=redis://localhost:6379/0                       # required
FEATURE_NEW_CHECKOUT=false                               # optional, default false
LOG_LEVEL=info                                           # optional, default info
```

---

## Logging

- Logs MUST be written to stdout as a stream of time-ordered events. The execution
  environment (not the application) is responsible for routing, storing, and aggregating them.
- Every log line MUST be structured (JSON or a key=value format). Free-form prose MUST NOT
  be the primary log format.
- Every log line SHOULD include: `timestamp` (ISO 8601 UTC), `level`, `service`, `trace_id`,
  `span_id`, and a concise `message`.
- Passwords, tokens, credit card numbers, and other secrets MUST NOT appear in logs.
  Personally-identifiable information (PII) SHOULD be omitted or replaced with an opaque
  identifier.
- Log volume MUST be controlled. Informational or debug logs in hot paths SHOULD use
  sampling or be gated behind a runtime log-level flag. Error logs MUST always be emitted.
- Log levels MUST be used consistently: `DEBUG` for developer diagnostics, `INFO` for normal
  operations, `WARN` for recoverable anomalies, `ERROR` for failures that require attention.

**Example — structured log line:**

```json
{
  "timestamp": "2026-06-12T10:04:33.421Z",
  "level": "error",
  "service": "order-api",
  "trace_id": "4bf92f3577b34da6",
  "span_id": "00f067aa0ba902b7",
  "message": "payment charge failed",
  "order_id": "ord_8821",
  "error": "upstream timeout after 3000ms"
}
```

---

## Error Handling

- Errors MUST NOT be silently swallowed. Every caught error MUST either be handled
  (recovered) or re-raised with context added.
- Services MUST return structured error responses that include a stable machine-readable
  code and a human-readable message. HTTP APIs SHOULD follow RFC 9457 (Problem Details).
- Internal error details (stack traces, SQL queries, system paths) MUST NOT be exposed in
  responses to external callers. Log them internally; return only a safe summary externally.
- Validation errors from user input MUST be distinguished from internal errors. HTTP APIs
  MUST use `4xx` for client errors and `5xx` for server faults.
- Error responses MUST include a `trace_id` so callers can correlate a failing request to
  server-side logs.

**Example — structured error response:**

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "quantity must be greater than 0",
  "trace_id": "4bf92f3577b34da6"
}
```

---

## Resilience

- Services MUST assume that downstream dependencies (databases, caches, third-party APIs)
  will fail intermittently.
- Critical paths MUST implement a circuit breaker: after a threshold of consecutive failures,
  stop sending requests to the failing dependency and return a fast error until the dependency
  recovers.
- Services SHOULD implement bulkheads — isolate resources (thread pools, connection pools)
  used for different downstream calls so one slow dependency cannot exhaust shared capacity.
- Non-critical features MUST degrade gracefully when their backing service is unavailable
  rather than failing the entire request.

**Example — circuit breaker states:**

```
CLOSED (normal) → failures exceed threshold → OPEN (fast-fail)
OPEN → timeout elapsed → HALF-OPEN (probe one request)
HALF-OPEN → probe succeeds → CLOSED
HALF-OPEN → probe fails → OPEN
```

---

## Timeouts

- Every outbound network call MUST have an explicit timeout. No call MUST rely on the
  platform default (which is often infinite).
- Services MUST set timeouts at two levels where applicable: connection timeout (time to
  establish a connection) and read/request timeout (time to receive the full response).
- Timeout values MUST be configurable via environment variables, not hard-coded.
- Services SHOULD propagate deadline budgets via request context so that inner calls respect
  the remaining budget of the outer call.

**Example — timeout budget propagation:**

```
Incoming request has a 5s deadline.
  ↓ passes remaining budget (4.8s) to downstream call A
    ↓ passes remaining budget (3.1s) to downstream call B
If budget is already exhausted, call B is skipped immediately.
```

---

## Retries

- Transient failures on idempotent operations SHOULD be retried automatically. Non-idempotent
  operations MUST NOT be retried without explicit idempotency guarantees.
- Retries MUST use exponential backoff with jitter to avoid synchronized retry storms.
- Retries MUST have a maximum attempt limit. Services MUST NOT retry indefinitely.
- The `Retry-After` header (or equivalent in other protocols) MUST be respected when
  returned by a downstream service.
- `429 Too Many Requests` and `503 Service Unavailable` responses SHOULD be retried.
  `4xx` client errors (except `408` and `429`) MUST NOT be retried.

**Example — backoff with jitter:**

```
attempt 1: wait = base_delay * 2^0 + rand(0, jitter) = ~100ms
attempt 2: wait = base_delay * 2^1 + rand(0, jitter) = ~200ms
attempt 3: wait = base_delay * 2^2 + rand(0, jitter) = ~400ms
max_attempts = 4; give up after attempt 4
```

---

## Idempotency

- All mutation endpoints (POST creating a resource, any endpoint that changes state) SHOULD
  support idempotency keys so that clients can safely retry on network failure.
- Services MUST be able to detect a duplicate request (via idempotency key or natural
  deduplication on a unique business key) and return the same result without re-executing
  side effects.
- Idempotency keys MUST be stored with the operation result long enough for a retry window
  (typically 24 hours).
- Database writes triggered by events MUST be guarded by an idempotency check. Message
  queues deliver at-least-once; consumers MUST handle duplicate delivery.

**Example — idempotency key header:**

```http
POST /charges
Idempotency-Key: a8098c1a-f86e-11da-bd1a-00112444be1e
Content-Type: application/json

{ "amount": 1000, "currency": "USD", "source": "tok_visa" }
```

---

## Background Jobs

- Background jobs MUST be idempotent. A job that runs twice MUST produce the same
  outcome as running once.
- Jobs MUST have a timeout. A job that never completes MUST be killed and re-enqueued or
  dead-lettered.
- Jobs MUST emit structured logs and, on failure, record the error with a stack trace before
  re-raising or moving the job to a dead-letter queue.
- Long-running jobs SHOULD be broken into smaller units of work that can be checkpointed
  so that a restart does not replay the entire job.
- Job queues MUST be monitored. Queue depth, job latency, and dead-letter count MUST be
  tracked as metrics.

---

## Health Checks

- Every service MUST expose at minimum two health endpoints:
  - `GET /healthz` (liveness): returns `200` if the process is alive and able to serve requests.
    MUST NOT check dependencies.
  - `GET /readyz` (readiness): returns `200` only when the service is ready to accept traffic
    (dependencies reachable, migrations complete, caches warm).
- Liveness and readiness probes MUST be fast (respond within 500ms).
- Health endpoints MUST NOT require authentication.
- A deep health check endpoint (`GET /healthz/deep`) MAY be provided for internal diagnostic
  use. It SHOULD check each critical dependency and report its status.

**Example — readiness response:**

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "migrations": "ok"
  }
}
```

---

## Observability

Services MUST be observable through three telemetry pillars.

### Metrics

- Services MUST expose metrics covering: request rate, error rate, and latency (p50, p95,
  p99) per endpoint.
- Infrastructure metrics (CPU, memory, connection pool saturation, queue depth) MUST also
  be collected.
- Metrics MUST be tagged with at minimum: `service`, `environment`, `version`, and
  per-operation dimensions where applicable.
- Alerts MUST be defined on error rate and latency SLOs, not just raw error counts.

### Traces

- Every inbound request MUST generate a trace. Trace context (`trace-id`, `span-id`) MUST be
  propagated to all downstream calls via standard headers (W3C `traceparent` or `B3`).
- Traces MUST capture: span name, start time, duration, HTTP status (or equivalent), and
  error status.
- Database queries, cache operations, and outbound HTTP calls SHOULD each be wrapped in
  their own child span.

### Logs

See the [Logging](#logging) section. Logs MUST include `trace_id` so log entries can be
joined to trace spans.

**Example — W3C trace propagation header:**

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

---

## Deployment Readiness

- The build, release, and run stages MUST be strictly separated. A release artifact MUST be
  immutable — no code changes after build, no differences between staging and production
  artifacts.
- Services MUST support rolling or blue/green deployments. A new instance MUST be able to
  come up alongside the old one with no shared mutable state or port conflicts.
- Database schema migrations MUST be backward-compatible with the previous version of the
  service. Deploy migrations before deploying the new service binary, not as part of service
  startup. This ensures the old version keeps working during a rollout.
- Services MUST handle `SIGTERM` with a graceful shutdown: stop accepting new connections,
  finish in-flight requests (with a bounded drain timeout), release locks, and exit with code 0.
- Every service MUST have a documented rollback procedure. A rollback MUST be achievable
  by redeploying the previous release artifact without manual data surgery.
- Development, staging, and production MUST use the same base image, same runtime
  version, and the same configuration mechanism. Environment-specific behavior MUST come
  from environment variable values, not from code branches.

**Example — graceful shutdown sequence:**

```
1. Receive SIGTERM
2. Stop accepting new connections (deregister from load balancer / remove readiness)
3. Wait for in-flight requests to complete (drain_timeout = 30s)
4. Close database connections and release any distributed locks
5. Flush metrics and traces
6. Exit 0
```
