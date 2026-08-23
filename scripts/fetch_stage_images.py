#!/usr/bin/env python3
"""Fetch the pipeline-stage images and record where every one of them came from.

Sources CC0 and public-domain Islamic art and architecture from Openverse, crops
to a consistent aspect, converts to WebP, and writes a credits manifest.

    python3 scripts/fetch_stage_images.py

Every planning document requires outside materials, licences, and provenance to
be disclosed, so the manifest is the point of this script as much as the images
are. Nothing is committed without a recorded licence and source URL.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "apps" / "web" / "public" / "media" / "stages"
MANIFEST_PATH = REPO_ROOT / "docs" / "media-credits.json"

USER_AGENT = "project-amanah/0.1 (hackathon prototype)"
REQUEST_TIMEOUT_SECONDS = 40

# Only these licences may be committed. Both allow redistribution without a
# per-use permission grant; attribution is recorded regardless.
# CC-BY is included because the CC0 pool for these subjects is too thin to
# cover five stages. Attribution is recorded for every image either way, and
# the planning documents already require outside materials to be disclosed.
PERMITTED_LICENSES = {"cc0", "pdm", "by"}

TARGET_WIDTH = 1200
TARGET_ASPECT = 3 / 2
WEBP_QUALITY = 82
MINIMUM_SOURCE_WIDTH = 900


@dataclass(frozen=True)
class StageImage:
    """One pipeline stage and the imagery that should represent it."""

    slug: str
    queries: tuple[str, ...]
    alt: str


STAGES = (
    StageImage(
        slug="capture",
        queries=("camera lens photographer", "vintage camera photography"),
        alt="A camera lens, focused.",
    ),
    StageImage(
        slug="classify",
        queries=("colouring pencils", "coloured pencils arranged row"),
        alt="Coloured pencils laid out in ordered rows.",
    ),
    StageImage(
        slug="contextualize",
        queries=("world map pins", "map of the world"),
        alt="A world map marked with pins.",
    ),
    StageImage(
        slug="review",
        queries=("manuscript proofreading pen", "annotated manuscript page"),
        alt="A manuscript page marked up by hand.",
    ),
    StageImage(
        slug="report",
        # No faces: the methodology section states that no identifiable person
        # appears on this page, and a newspaper front page routinely carries one.
        queries=("print order book", "letterpress metal type", "printed text typography closeup"),
        alt="Printed type, set and inked.",
    ),
)


def _search(query: str) -> list[dict]:
    url = (
        "https://api.openverse.org/v1/images/?q="
        + urllib.parse.quote(query)
        + "&license="
        + ",".join(sorted(PERMITTED_LICENSES))
        + "&page_size=8&mature=false"
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response).get("results") or []


def _choose(results: list[dict], already_used: set[str]) -> dict | None:
    """First result that is licensed as expected, large enough, and not reused.

    Openverse returns overlapping results across related queries, so without the
    dedupe one artwork ends up standing in for two different stages.
    """
    for item in results:
        width = item.get("width") or 0
        if (
            item.get("license") in PERMITTED_LICENSES
            and width >= MINIMUM_SOURCE_WIDTH
            and item.get("id") not in already_used
        ):
            return item
    return None


def _download(url: str) -> Image.Image:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return Image.open(BytesIO(response.read())).convert("RGB")


def _crop_to_aspect(image: Image.Image) -> Image.Image:
    """Centre-crop to the target aspect, then scale to the target width."""
    target_height = image.width / TARGET_ASPECT
    if target_height <= image.height:
        offset = (image.height - target_height) / 2
        box = (0, offset, image.width, offset + target_height)
    else:
        target_width = image.height * TARGET_ASPECT
        offset = (image.width - target_width) / 2
        box = (offset, 0, offset + target_width, image.height)

    cropped = image.crop(tuple(round(value) for value in box))
    height = round(TARGET_WIDTH / TARGET_ASPECT)
    return cropped.resize((TARGET_WIDTH, height), Image.LANCZOS)


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    credits: list[dict] = []
    already_used: set[str] = set()

    for stage in STAGES:
        chosen = None
        for query in stage.queries:
            chosen = _choose(_search(query), already_used)
            if chosen is not None:
                break
        if chosen is None:
            print(f"  {stage.slug:14s} no permissively licensed result, skipped")
            continue

        already_used.add(chosen.get("id"))
        image = _crop_to_aspect(_download(chosen["url"]))
        destination = OUTPUT_DIR / f"{stage.slug}.webp"
        image.save(destination, "WEBP", quality=WEBP_QUALITY, method=6)

        size_kb = destination.stat().st_size / 1024
        print(f"  {stage.slug:14s} {image.width}x{image.height}  {size_kb:5.0f} KB  [{chosen['license']}]")

        credits.append(
            {
                "stage": stage.slug,
                "file": f"media/stages/{stage.slug}.webp",
                "alt": stage.alt,
                "title": chosen.get("title"),
                "creator": chosen.get("creator"),
                "license": chosen.get("license"),
                "license_version": chosen.get("license_version"),
                "license_url": chosen.get("license_url"),
                "source": chosen.get("source"),
                "foreign_landing_url": chosen.get("foreign_landing_url"),
                "original_url": chosen.get("url"),
                "openverse_id": chosen.get("id"),
            }
        )

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(credits, indent=2) + "\n")
    print(f"\nCredits written to {MANIFEST_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    build()
