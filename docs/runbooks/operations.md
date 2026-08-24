# Operating resilience and observability

Last reviewed: 2026-08-23

The API emits single-line JSON. Requests carry `request_id`; ETL stages also
carry `run_id`, `job_id`, `stage`, and safe source key. Content, prompts, text,
URLs, tokens, credentials, passwords, and secrets are redacted before output.
Tracebacks are never serialized.

## Metrics

| Metric | Safe labels | Use |
|---|---|---|
| `api_requests_total` | method, route, status class | traffic/errors |
| `api_request_duration_ms` | method, route, status class | latency |
| `connector_runs_total`, `connector_failures_total` | source, outcome | provider isolation |
| `gemini_outcomes_total` | outcome | deferral/failure/budget |
| `jobs_total` | stage, state | retries, leases, dead letters |
| `contributions_total` | action, outcome | anti-abuse |
| `review_queue_events_total` | action, outcome | review workload |
| `report_events_total` | action, outcome | report failures |
| `coverage_score` | source, mode | stale/partial collection |

There is no public metrics route because only health and readiness may be
anonymous. Aggregate stable metric events in the log collector.

## Alerts and response

- Alert after two missed eight-hour windows. Preserve last success and its
  timestamp; never substitute fixtures.
- On quota/provider failure, stop only that connector, keep its checkpoint, and
  publish a safe code/coverage warning.
- Alert on retry-wait age, expired leases, and dead-letter growth. A worker that
  loses a lease drops its result.
- Gemini deferral or budget exhaustion must not block deterministic metrics.
- For a suspected secret or harmful-content leak, restrict access, rotate the
  affected credential/signed URL, preserve safe IDs only, remove the unsafe
  projection/artifact, and complete source-policy/deletion review before restore.
