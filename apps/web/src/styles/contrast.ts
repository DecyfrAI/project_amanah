/**
 * WCAG 2.2 relative-luminance and contrast-ratio maths.
 *
 * PROJECT_AMANAH_BRAND_DESIGN_SYSTEM.md 4 requires every final foreground and
 * background pair to be verified against WCAG 2.2 AA, and 9 sets the specific
 * targets. This module supplies the arithmetic; tokens.contrast.test.ts applies
 * it to the real token file so the requirement is enforced rather than asserted.
 *
 * Reference: https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
 */

/** AA minimum for body text (WCAG 1.4.3). */
export const CONTRAST_AA_NORMAL_TEXT = 4.5;

/** AA minimum for large text, 18.66px bold or 24px regular and above. */
export const CONTRAST_AA_LARGE_TEXT = 3;

/** AA minimum for UI components and meaningful graphics (WCAG 1.4.11). */
export const CONTRAST_AA_NON_TEXT = 3;

export interface Rgb {
  red: number;
  green: number;
  blue: number;
}

const SHORT_HEX_LENGTH = 3;
const FULL_HEX_LENGTH = 6;

/**
 * Parse a three- or six-digit hex colour into 0-255 channels.
 *
 * @throws if the value is not a hex colour, callers pass token values, and a
 * silent fallback would let a malformed token pass the contrast gate.
 */
export function parseHexColor(hex: string): Rgb {
  const normalized = hex.trim().replace(/^#/, '');

  const expanded =
    normalized.length === SHORT_HEX_LENGTH
      ? normalized
          .split('')
          .map((character) => character + character)
          .join('')
      : normalized;

  if (expanded.length !== FULL_HEX_LENGTH || !/^[0-9a-f]{6}$/i.test(expanded)) {
    throw new Error(`Expected a hex colour such as "#0e9fa3", received "${hex}"`);
  }

  return {
    red: Number.parseInt(expanded.slice(0, 2), 16),
    green: Number.parseInt(expanded.slice(2, 4), 16),
    blue: Number.parseInt(expanded.slice(4, 6), 16),
  };
}

const LOW_CHANNEL_THRESHOLD = 0.04045;
const LOW_CHANNEL_DIVISOR = 12.92;
const GAMMA_OFFSET = 0.055;
const GAMMA_DIVISOR = 1.055;
const GAMMA_EXPONENT = 2.4;

function linearizeChannel(channel: number): number {
  const proportion = channel / 255;
  return proportion <= LOW_CHANNEL_THRESHOLD
    ? proportion / LOW_CHANNEL_DIVISOR
    : Math.pow((proportion + GAMMA_OFFSET) / GAMMA_DIVISOR, GAMMA_EXPONENT);
}

const LUMINANCE_RED_COEFFICIENT = 0.2126;
const LUMINANCE_GREEN_COEFFICIENT = 0.7152;
const LUMINANCE_BLUE_COEFFICIENT = 0.0722;

/** Relative luminance of a colour, 0 (black) to 1 (white). */
export function relativeLuminance({ red, green, blue }: Rgb): number {
  return (
    LUMINANCE_RED_COEFFICIENT * linearizeChannel(red) +
    LUMINANCE_GREEN_COEFFICIENT * linearizeChannel(green) +
    LUMINANCE_BLUE_COEFFICIENT * linearizeChannel(blue)
  );
}

const CONTRAST_OFFSET = 0.05;

/** Contrast ratio between two hex colours, from 1:1 to 21:1. */
export function contrastRatio(foregroundHex: string, backgroundHex: string): number {
  const foreground = relativeLuminance(parseHexColor(foregroundHex));
  const background = relativeLuminance(parseHexColor(backgroundHex));

  const lighter = Math.max(foreground, background);
  const darker = Math.min(foreground, background);

  return (lighter + CONTRAST_OFFSET) / (darker + CONTRAST_OFFSET);
}
