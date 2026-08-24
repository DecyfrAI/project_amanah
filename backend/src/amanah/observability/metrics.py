"""Documented operational metrics emitted as redacted structured events.

The service deliberately does not add an anonymous ``/metrics`` route: only the
two health endpoints may bypass authentication. Production log aggregation can
count and histogram these stable event names without receiving source content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger("amanah.metrics")


class MetricName(StrEnum):
    api_requests = "api_requests_total"
    api_duration = "api_request_duration_ms"
    connector_runs = "connector_runs_total"
    connector_failures = "connector_failures_total"
    gemini_outcomes = "gemini_outcomes_total"
    jobs = "jobs_total"
    contributions = "contributions_total"
    review_queue = "review_queue_events_total"
    reports = "report_events_total"
    coverage = "coverage_score"


@dataclass(frozen=True, slots=True)
class MetricEvent:
    name: MetricName
    value: int | float
    labels: dict[str, str]


def record_metric(name: MetricName, value: int | float = 1, **labels: object) -> MetricEvent:
    """Emit one allow-listed metric event without user/source content."""
    safe_labels = {
        key: str(label)
        for key, label in labels.items()
        if label is not None
        and key
        in {
            "method",
            "route",
            "status_class",
            "source_key",
            "stage",
            "state",
            "outcome",
            "action",
            "data_mode",
        }
    }
    event = MetricEvent(name=name, value=value, labels=safe_labels)
    logger.info(
        "operational metric",
        extra={"metric_name": name.value, "metric_value": value, "metric_labels": safe_labels},
    )
    return event
