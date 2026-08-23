/**
 * Contrast gate for the design tokens.
 *
 * Reads the real tokens.css, resolves each semantic token to a concrete hex
 * value, and asserts the pairs the interface actually renders. Changing a
 * palette value badly fails the build here rather than in an audit later.
 *
 * Covers PROJECT_AMANAH_BRAND_DESIGN_SYSTEM.md 4 ("Verify all final
 * foreground/background pairs against WCAG 2.2 AA") and 9.
 */

import { readFileSync } from 'node:fs';
import { resolve as resolvePath } from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  CONTRAST_AA_LARGE_TEXT,
  CONTRAST_AA_NON_TEXT,
  CONTRAST_AA_NORMAL_TEXT,
  contrastRatio,
} from './contrast';

type TokenMap = ReadonlyMap<string, string>;

// jsdom does not give import.meta.url a file scheme, so resolve from the
// Vitest working directory, which is the apps/web project root.
const TOKENS_CSS = readFileSync(resolvePath(process.cwd(), 'src/styles/tokens.css'), 'utf8');

/**
 * Extract the custom properties declared in one selector block.
 *
 * The dark theme redeclares the same token names, so scoping the scan to a
 * single block is what keeps the two themes independently checkable.
 */
function readTokenBlock(selector: string): TokenMap {
  const blockStart = TOKENS_CSS.indexOf(selector);
  if (blockStart === -1) {
    throw new Error(`tokens.css has no "${selector}" block`);
  }

  const openBrace = TOKENS_CSS.indexOf('{', blockStart);
  const closeBrace = TOKENS_CSS.indexOf('\n}', openBrace);
  const body = TOKENS_CSS.slice(openBrace, closeBrace);

  const declarations = new Map<string, string>();
  for (const [, name, value] of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    declarations.set(name!.trim(), value!.trim());
  }
  return declarations;
}

/** Follow `var(--x)` indirection until a literal colour is reached. */
function resolve(tokens: TokenMap, name: string, fallback?: TokenMap): string {
  const seen = new Set<string>();
  let current = name;

  for (;;) {
    if (seen.has(current)) {
      throw new Error(`Token ${name} resolves in a cycle at ${current}`);
    }
    seen.add(current);

    const value = tokens.get(current) ?? fallback?.get(current);
    if (value === undefined) {
      throw new Error(`Token ${current} is not declared`);
    }

    const reference = /^var\((--[\w-]+)\)$/.exec(value);
    if (reference === null) {
      return value;
    }
    current = reference[1]!;
  }
}

const lightTokens = readTokenBlock(':root {');
const darkTokens = readTokenBlock(":root[data-theme='dark']");

interface ContrastCase {
  readonly label: string;
  readonly foreground: string;
  readonly background: string;
  readonly minimum: number;
}

/** Pairs the interface genuinely renders, per the dashboard style spec. */
const CONTRAST_CASES: readonly ContrastCase[] = [
  // Body and secondary text on both page and card surfaces.
  {
    label: 'primary text on page',
    foreground: '--color-text-primary',
    background: '--color-page',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'primary text on surface',
    foreground: '--color-text-primary',
    background: '--color-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'secondary text on page',
    foreground: '--color-text-secondary',
    background: '--color-page',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'secondary text on surface',
    foreground: '--color-text-secondary',
    background: '--color-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  // Muted text is reserved for large or non-essential metadata.
  {
    label: 'muted text on surface',
    foreground: '--color-text-muted',
    background: '--color-surface',
    minimum: CONTRAST_AA_LARGE_TEXT,
  },
  // Accent as a link colour, and as a filled button.
  {
    label: 'accent text on page',
    foreground: '--color-accent',
    background: '--color-page',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'accent text on surface',
    foreground: '--color-accent',
    background: '--color-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'text on accent fill',
    foreground: '--color-text-on-accent',
    background: '--color-accent',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  // Status colours carry meaning, so each must clear normal-text AA on the
  // surface it labels, colour is never the only cue, but it must still be read.
  {
    label: 'harm status on its surface',
    foreground: '--color-status-harm',
    background: '--color-status-harm-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'review status on its surface',
    foreground: '--color-status-review',
    background: '--color-status-review-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'confirmed status on its surface',
    foreground: '--color-status-confirmed',
    background: '--color-status-confirmed-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  {
    label: 'emerging status on its surface',
    foreground: '--color-status-emerging',
    background: '--color-status-emerging-surface',
    minimum: CONTRAST_AA_NORMAL_TEXT,
  },
  // Chart marks are meaningful graphics under WCAG 1.4.11.
  {
    label: 'primary chart series on surface',
    foreground: '--color-chart-primary',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'emerging chart series on surface',
    foreground: '--color-chart-emerging',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'emerging chart series on page',
    foreground: '--color-chart-emerging',
    background: '--color-page',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'primary chart series on page',
    foreground: '--color-chart-primary',
    background: '--color-page',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'categorical chart 1 on surface',
    foreground: '--color-chart-cat-1',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'categorical chart 2 on surface',
    foreground: '--color-chart-cat-2',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'categorical chart 3 on surface',
    foreground: '--color-chart-cat-3',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'categorical chart 4 on surface',
    foreground: '--color-chart-cat-4',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'categorical chart 5 on surface',
    foreground: '--color-chart-cat-5',
    background: '--color-surface',
    minimum: CONTRAST_AA_NON_TEXT,
  },
  {
    label: 'focus ring on page',
    foreground: '--color-focus-ring',
    background: '--color-page',
    minimum: CONTRAST_AA_NON_TEXT,
  },
];

describe.each([
  { theme: 'light', tokens: lightTokens, fallback: undefined },
  { theme: 'dark', tokens: darkTokens, fallback: lightTokens },
])('$theme theme contrast', ({ tokens, fallback }) => {
  it.each(CONTRAST_CASES)('$label meets $minimum:1', ({ foreground, background, minimum }) => {
    const ratio = contrastRatio(
      resolve(tokens, foreground, fallback),
      resolve(tokens, background, fallback),
    );

    expect(ratio).toBeGreaterThanOrEqual(minimum);
  });
});

describe('token block parsing', () => {
  it('finds both theme blocks', () => {
    expect(lightTokens.size).toBeGreaterThan(0);
    expect(darkTokens.size).toBeGreaterThan(0);
  });

  it('rejects a token that resolves in a cycle', () => {
    const cyclic: TokenMap = new Map([
      ['--a', 'var(--b)'],
      ['--b', 'var(--a)'],
    ]);

    expect(() => resolve(cyclic, '--a')).toThrow(/cycle/);
  });

  it('rejects a token that is not declared', () => {
    expect(() => resolve(new Map(), '--missing')).toThrow(/not declared/);
  });
});
