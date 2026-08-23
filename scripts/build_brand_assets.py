#!/usr/bin/env python3
"""Derive the Project Amanah brand asset set from the two source logo files.

Reads the light-theme logo and the original dark-theme logo from brand/source/,
applies the dark-theme gold correction, and writes every derived asset the
frontend needs into apps/web/public/brand/.

Re-run this whenever a source logo changes:

    python3 scripts/build_brand_assets.py

Asset requirements come from PROJECT_AMANAH_FRONTEND_DEVELOPMENT_PLAN.md 7
("Required brand assets") and PROJECT_AMANAH_BRAND_DESIGN_SYSTEM.md 3
("Logo direction"), including the clear-space rule and minimum sizes.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "brand" / "source"
OUTPUT_DIR = REPO_ROOT / "apps" / "web" / "public" / "brand"

LIGHT_SOURCE = SOURCE_DIR / "logo-light-theme.png"
DARK_SOURCE = SOURCE_DIR / "logo-dark-theme-original.png"

# The dark-theme logo shipped at hsl(60, 100%, 81%), pure yellow, not a lighter
# form of the brand gold at hsl(41, 86%, 48%). Retargeting to the brand hue and
# saturation, lifted in lightness for dark surfaces, yields #F6D96E.
GOLD_TARGET_HUE = 44 / 360
GOLD_TARGET_SATURATION = 0.86
GOLD_TARGET_LIGHTNESS = 0.69
GOLD_SOURCE_LIGHTNESS = 0.808

YELLOW_HUE_RANGE = (40 / 360, 80 / 360)
YELLOW_MIN_SATURATION = 0.12

# Pixels below this alpha are anti-aliasing haze, not content.
CONTENT_ALPHA_THRESHOLD = 12

# A run of empty columns at least this wide separates the symbol from the wordmark.
MIN_GAP_WIDTH = 40

# Brand system 3: clear space is at least the height of the capital "A".
# The wordmark's cap height is very close to half its full trimmed height.
CLEAR_SPACE_RATIO = 0.5

WORDMARK_EXPORT_WIDTH = 720
MARK_EXPORT_SIZE = 512
STACKED_EXPORT_WIDTH = 512
FAVICON_SIZES = (16, 32, 180, 512)

# Stacked lockup: symbol above, wordmark below, both centred on a shared axis.
# The wordmark is set to this multiple of the symbol's width so neither element
# dominates, and separated by this fraction of the symbol's height.
STACKED_WORDMARK_WIDTH_RATIO = 2.2
STACKED_GAP_RATIO = 0.18

# The favicon tile is tighter than the clear-space rule so the mark stays legible
# at 16-32 px, where surrounding padding is wasted pixels.
FAVICON_PADDING_RATIO = 0.16
FAVICON_CORNER_RADIUS_RATIO = 0.22
NAVY_950 = (7, 26, 43, 255)


@dataclass(frozen=True)
class LogoRegions:
    """Pixel bounds of the two logo elements within a source image."""

    symbol: tuple[int, int, int, int]
    wordmark: tuple[int, int, int, int]
    full: tuple[int, int, int, int]


def correct_dark_theme_gold(image: Image.Image) -> Image.Image:
    """Retarget the dark-theme yellow to the brand gold hue.

    Lightness is remapped through the darkness domain so the white end of each
    anti-aliased edge stays white while the solid core lands on the target.
    """
    corrected = image.copy()
    pixels = corrected.load()
    if pixels is None:
        raise RuntimeError(f"Could not access pixel data for {image}")

    darkness_scale = (1 - GOLD_TARGET_LIGHTNESS) / (1 - GOLD_SOURCE_LIGHTNESS)
    hue_min, hue_max = YELLOW_HUE_RANGE

    for y in range(corrected.height):
        for x in range(corrected.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                continue
            hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
            if not (hue_min <= hue <= hue_max and saturation > YELLOW_MIN_SATURATION):
                continue
            new_lightness = 1 - min(1.0, (1 - lightness) * darkness_scale)
            new_saturation = saturation * GOLD_TARGET_SATURATION
            new_red, new_green, new_blue = colorsys.hls_to_rgb(
                GOLD_TARGET_HUE, new_lightness, new_saturation
            )
            pixels[x, y] = (
                round(new_red * 255),
                round(new_green * 255),
                round(new_blue * 255),
                alpha,
            )

    return corrected


def _content_columns(image: Image.Image) -> list[bool]:
    alpha = image.split()[3].load()
    if alpha is None:
        raise RuntimeError("Could not access alpha channel")
    return [
        any(alpha[x, y] > CONTENT_ALPHA_THRESHOLD for y in range(image.height))
        for x in range(image.width)
    ]


def _trim_bounds(image: Image.Image, x_start: int, x_end: int) -> tuple[int, int, int, int]:
    """Tight bounds of real content within a horizontal slice."""
    alpha = image.split()[3].load()
    if alpha is None:
        raise RuntimeError("Could not access alpha channel")

    top, bottom = image.height, 0
    left, right = x_end, x_start
    for x in range(x_start, x_end):
        for y in range(image.height):
            if alpha[x, y] > CONTENT_ALPHA_THRESHOLD:
                top = min(top, y)
                bottom = max(bottom, y)
                left = min(left, x)
                right = max(right, x)
    return (left, top, right + 1, bottom + 1)


def locate_regions(image: Image.Image) -> LogoRegions:
    """Split the horizontal lockup into its symbol and wordmark halves."""
    occupied = _content_columns(image)
    filled = [x for x, has_content in enumerate(occupied) if has_content]
    if not filled:
        raise ValueError("Logo image contains no visible content")
    content_start, content_end = filled[0], filled[-1] + 1

    gaps: list[tuple[int, int]] = []
    run_start: int | None = None
    for x in range(content_start, content_end):
        if occupied[x]:
            if run_start is not None and x - run_start >= MIN_GAP_WIDTH:
                gaps.append((run_start, x))
            run_start = None
        elif run_start is None:
            run_start = x

    if not gaps:
        raise ValueError("Could not find a gap separating the symbol from the wordmark")

    widest_gap = max(gaps, key=lambda gap: gap[1] - gap[0])
    split_x = (widest_gap[0] + widest_gap[1]) // 2

    return LogoRegions(
        symbol=_trim_bounds(image, content_start, split_x),
        wordmark=_trim_bounds(image, split_x, content_end),
        full=_trim_bounds(image, content_start, content_end),
    )


def _with_clear_space(image: Image.Image, bounds: tuple[int, int, int, int]) -> Image.Image:
    cropped = image.crop(bounds)
    padding = round(cropped.height * CLEAR_SPACE_RATIO)
    padded = Image.new(
        "RGBA", (cropped.width + padding * 2, cropped.height + padding * 2), (0, 0, 0, 0)
    )
    padded.alpha_composite(cropped, (padding, padding))
    return padded


def _to_square(
    image: Image.Image, bounds: tuple[int, int, int, int], padding_ratio: float
) -> Image.Image:
    cropped = image.crop(bounds)
    side = round(max(cropped.width, cropped.height) * (1 + padding_ratio))
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.alpha_composite(
        cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2)
    )
    return square


def _build_stacked(image: Image.Image, regions: LogoRegions) -> Image.Image:
    """Compose the vertical lockup from the horizontal source.

    The source ships side by side, so the symbol and the wordmark are lifted out
    and restacked rather than redrawn. Both are centred on one vertical axis,
    which is what makes the lockup read as a single object in a narrow column such
    as a sidebar. Clear space follows the same cap-height rule as the horizontal
    export, measured from the wordmark.
    """
    symbol = image.crop(regions.symbol)
    wordmark = image.crop(regions.wordmark)

    wordmark_width = round(symbol.width * STACKED_WORDMARK_WIDTH_RATIO)
    wordmark_height = round(wordmark.height * wordmark_width / wordmark.width)
    wordmark = wordmark.resize((wordmark_width, wordmark_height), Image.LANCZOS)

    gap = round(symbol.height * STACKED_GAP_RATIO)
    padding = round(wordmark_height * CLEAR_SPACE_RATIO)
    content_width = max(symbol.width, wordmark_width)

    stacked = Image.new(
        "RGBA",
        (
            content_width + padding * 2,
            symbol.height + gap + wordmark_height + padding * 2,
        ),
        (0, 0, 0, 0),
    )
    stacked.alpha_composite(symbol, (padding + (content_width - symbol.width) // 2, padding))
    stacked.alpha_composite(
        wordmark,
        (padding + (content_width - wordmark_width) // 2, padding + symbol.height + gap),
    )
    return stacked


def _build_favicon_tile(dark: Image.Image, regions: LogoRegions) -> Image.Image:
    """Compose the favicon as the inverse mark on a navy tile.

    A bare teal mark disappears against dark browser chrome and a bare cyan mark
    disappears against light chrome. An opaque brand-navy tile reads correctly on
    both, and lets the mark fill more of the icon at 16-32 px.
    """
    mark = _to_square(dark, regions.symbol, FAVICON_PADDING_RATIO)
    tile = Image.new("RGBA", mark.size, NAVY_950)

    corner_radius = round(mark.width * FAVICON_CORNER_RADIUS_RATIO)
    rounded = Image.new("L", mark.size, 0)
    ImageDraw.Draw(rounded).rounded_rectangle(
        (0, 0, mark.width - 1, mark.height - 1), radius=corner_radius, fill=255
    )
    tile.putalpha(rounded)
    tile.alpha_composite(mark)
    return tile


def _save_at_width(image: Image.Image, width: int, destination: Path) -> None:
    height = round(image.height * width / image.width)
    resized = image.resize((width, height), Image.LANCZOS)
    resized.save(destination, optimize=True)
    print(f"  {destination.name:38s} {resized.width}x{resized.height}")


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    light = Image.open(LIGHT_SOURCE).convert("RGBA")
    dark = correct_dark_theme_gold(Image.open(DARK_SOURCE).convert("RGBA"))

    # Preserve the corrected dark master alongside the originals.
    dark.save(SOURCE_DIR / "logo-dark-theme.png", optimize=True)

    for label, image in (("light", light), ("dark", dark)):
        regions = locate_regions(image)
        suffix = "" if label == "light" else "-inverse"

        print(f"\n{label}-theme assets:")
        _save_at_width(
            _with_clear_space(image, regions.full),
            WORDMARK_EXPORT_WIDTH,
            OUTPUT_DIR / f"amanah-wordmark{suffix}.png",
        )
        _save_at_width(
            _to_square(image, regions.symbol, CLEAR_SPACE_RATIO),
            MARK_EXPORT_SIZE,
            OUTPUT_DIR / f"amanah-mark{suffix}.png",
        )
        _save_at_width(
            _build_stacked(image, regions),
            STACKED_EXPORT_WIDTH,
            OUTPUT_DIR / f"amanah-stacked{suffix}.png",
        )

    favicon = _build_favicon_tile(dark, locate_regions(dark))
    print("\nfavicons (inverse mark on a navy tile):")
    for size in FAVICON_SIZES:
        _save_at_width(favicon, size, OUTPUT_DIR / f"favicon-{size}.png")


if __name__ == "__main__":
    build()
