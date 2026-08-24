"""Request correlation and redacted structured logging (B-S4.3, B-S4.6)."""

import json
import logging

from amanah.observability.logging import JsonLogFormatter
from amanah.observability.metrics import MetricName, record_metric
from amanah.observability.request_context import bind_operation_context, resolve_request_id


def make_record(message: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="amanah.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )
    record.__dict__.update(extra)
    return record


def test_generated_request_id_is_prefixed_and_unique() -> None:
    first = resolve_request_id(None)
    second = resolve_request_id(None)

    assert first.startswith("req_")
    assert first != second


def test_safe_client_supplied_request_id_is_reused() -> None:
    assert resolve_request_id("req_abc-123") == "req_abc-123"


def test_unsafe_client_supplied_request_id_is_replaced() -> None:
    forged = 'req_1"}\n{"level":"error","message":"forged'

    resolved = resolve_request_id(forged)

    assert resolved != forged
    assert resolved.startswith("req_")


def test_oversized_client_supplied_request_id_is_replaced() -> None:
    assert resolve_request_id("a" * 65).startswith("req_")


def test_log_record_is_a_single_json_line() -> None:
    rendered = JsonLogFormatter().format(make_record("authentication failed", reason="expired"))

    assert "\n" not in rendered
    payload = json.loads(rendered)
    assert payload["message"] == "authentication failed"
    assert payload["reason"] == "expired"
    assert payload["level"] == "info"
    assert payload["service"] == "amanah-api"


def test_hostile_log_value_cannot_forge_a_second_line() -> None:
    rendered = JsonLogFormatter().format(
        make_record('user reported\n{"level":"error","message":"injected"}')
    )

    assert len(rendered.splitlines()) == 1
    assert json.loads(rendered)["message"].startswith("user reported")


def test_traceback_is_not_included_in_the_log_payload() -> None:
    try:
        raise ValueError("internal detail C:/secret/path.py")
    except ValueError as exc:
        record = make_record("unhandled server error")
        record.exc_info = (type(exc), exc, exc.__traceback__)

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["exception_type"] == "ValueError"
    assert "secret/path.py" not in json.dumps(payload)


def test_sensitive_extra_fields_are_redacted() -> None:
    payload = json.loads(
        JsonLogFormatter().format(
            make_record("provider failed", prompt="hostile source text", access_token="secret")
        )
    )

    assert payload["prompt"] == "[REDACTED]"
    assert payload["access_token"] == "[REDACTED]"
    assert "hostile source text" not in json.dumps(payload)


def test_run_and_job_context_is_attached_and_then_released() -> None:
    with bind_operation_context(run_id="run-1", job_id="job-1", stage="fetch"):
        inside = json.loads(JsonLogFormatter().format(make_record("stage complete")))
    outside = json.loads(JsonLogFormatter().format(make_record("request complete")))

    assert inside["run_id"] == "run-1"
    assert inside["job_id"] == "job-1"
    assert inside["stage"] == "fetch"
    assert "run_id" not in outside


def test_metric_events_keep_only_allowlisted_low_cardinality_labels() -> None:
    event = record_metric(
        MetricName.connector_runs,
        source_key="fixtures",
        outcome="succeeded",
        submitted_url="https://should-not-appear.example",
    )

    assert event.labels == {"source_key": "fixtures", "outcome": "succeeded"}
