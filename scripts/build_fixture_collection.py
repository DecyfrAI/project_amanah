#!/usr/bin/env python3
"""Generate the synthetic collection fixture the frontend reads in fixture mode.

Writes apps/web/src/fixtures/collection.json: sixty days of day-level, per-platform
counts that the fixture provider filters and aggregates exactly as the live API
would. The output is a generated artifact. Change this script, never the JSON.

    python3 scripts/build_fixture_collection.py

Nothing here is real. The counts come from a seeded generator, the containers are
invented, and no focal content appears at all: this file carries volumes only.
Item-level examples with redacted excerpts live in items.json, which is authored
by hand and reviewed.

Shape decisions worth knowing:

- A day that failed collection carries `collected: false` and no counts. Null is
  not zero, and the distinction has to survive all the way to the chart.
- Hate-type counts are the *primary* type per item, so they sum to the likely-hate
  count. Real classification is multi-label; the fixture does not pretend
  otherwise, it just carries one axis.
- Types and severity bands follow PROJECT_AMANAH_PROJECT_SPECIFICATION.md 244.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "apps" / "web" / "src" / "fixtures" / "collection.json"

SEED = 20260822
WINDOW_END = date(2026, 8, 16)
WINDOW_DAYS = 60

# Whole-day collection failures. Both are visible on screen as gaps and named in
# the coverage warnings, which is the point of having them.
GAP_DAYS = {date(2026, 7, 4), date(2026, 8, 7)}

HATE_TYPES = (
    "animosity",
    "derogation",
    "dehumanisation",
    "exclusion",
    "threat",
)

SEVERITY_BANDS = ("0", "1", "2", "3")


@dataclass(frozen=True)
class PlatformProfile:
    platform: str
    container_label: str
    containers: int
    observed_range: tuple[int, int]
    relevant_share: tuple[float, float]
    base_hate_share: tuple[float, float]


PLATFORMS = (
    PlatformProfile("youtube", "videos", 22, (78, 168), (0.18, 0.26), (0.14, 0.23)),
    PlatformProfile("reddit", "threads", 14, (36, 96), (0.22, 0.34), (0.11, 0.19)),
)

# A news event on 5 August that the rate coincides with. The dashboard must never
# call this a cause, and the fixture does not encode one: it lifts the hate share
# for a fortnight so the interface has a real pattern to describe carefully.
EVENT_START = date(2026, 8, 5)
EVENT_LIFT = 0.09
EVENT_DECAY_DAYS = 12


def _event_lift(day: date) -> float:
    if day < EVENT_START:
        return 0.0
    elapsed = (day - EVENT_START).days
    if elapsed > EVENT_DECAY_DAYS:
        return 0.0
    return EVENT_LIFT * (1 - elapsed / EVENT_DECAY_DAYS)


def _split(rng: random.Random, total: int, weights: tuple[float, ...]) -> list[int]:
    """Split a total across weighted buckets so the parts sum to the whole."""
    if total == 0:
        return [0] * len(weights)

    jittered = [weight * rng.uniform(0.7, 1.3) for weight in weights]
    scale = total / sum(jittered)
    parts = [int(value * scale) for value in jittered]

    remainder = total - sum(parts)
    for index in sorted(range(len(parts)), key=lambda i: -jittered[i])[:remainder]:
        parts[index] += 1
    return parts


def _platform_day(rng: random.Random, profile: PlatformProfile, day: date) -> dict[str, object]:
    observed = rng.randint(*profile.observed_range)
    relevant = round(observed * rng.uniform(*profile.relevant_share))
    hate_share = min(0.62, rng.uniform(*profile.base_hate_share) + _event_lift(day))
    likely_hate = round(relevant * hate_share)

    type_counts = dict(
        zip(HATE_TYPES, _split(rng, likely_hate, (0.32, 0.27, 0.16, 0.15, 0.10)), strict=True)
    )
    severity_counts = dict(
        zip(SEVERITY_BANDS, _split(rng, likely_hate, (0.34, 0.34, 0.22, 0.10)), strict=True)
    )

    # Older days have been through more of the queue. Reviewed items split into
    # confirmations and corrections; the rest are still awaiting a person.
    age = (WINDOW_END - day).days
    reviewed_share = min(0.95, 0.18 + age * 0.022)
    reviewed = round(likely_hate * reviewed_share)
    corrected = round(reviewed * rng.uniform(0.08, 0.2))

    return {
        "platform": profile.platform,
        "containers": profile.containers,
        "observed": observed,
        "relevant": relevant,
        "nonRelevant": observed - relevant,
        "likelyHate": likely_hate,
        "reviewConfirmed": reviewed - corrected,
        "reviewCorrected": corrected,
        "reviewPending": likely_hate - reviewed,
        "types": type_counts,
        "severity": severity_counts,
    }


def build() -> None:
    rng = random.Random(SEED)
    start = WINDOW_END - timedelta(days=WINDOW_DAYS - 1)

    days: list[dict[str, object]] = []
    for offset in range(WINDOW_DAYS):
        day = start + timedelta(days=offset)
        if day in GAP_DAYS:
            days.append({"date": day.isoformat(), "collected": False, "platforms": []})
            continue
        days.append(
            {
                "date": day.isoformat(),
                "collected": True,
                "platforms": [_platform_day(rng, profile, day) for profile in PLATFORMS],
            }
        )

    document = {
        "generatedBy": "scripts/build_fixture_collection.py",
        "available": {"from": start.isoformat(), "to": WINDOW_END.isoformat(), "timezone": "UTC"},
        "defaultWindowDays": 30,
        "lastSuccessfulRun": f"{WINDOW_END.isoformat()}T23:41:00+00:00",
        "platforms": [
            {
                "platform": profile.platform,
                "containerLabel": profile.container_label,
                "containers": profile.containers,
            }
            for profile in PLATFORMS
        ],
        "hateTypes": list(HATE_TYPES),
        "severityBands": list(SEVERITY_BANDS),
        "gapDays": sorted(day.isoformat() for day in GAP_DAYS),
        "days": days,
    }

    OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    collected = [day for day in days if day["collected"]]
    observed = sum(
        platform["observed"] for day in collected for platform in day["platforms"]  # type: ignore[index,union-attr]
    )
    print(f"  {OUTPUT.relative_to(REPO_ROOT)}")
    print(f"  {len(days)} days, {len(collected)} collected, {observed} items observed")


if __name__ == "__main__":
    build()
