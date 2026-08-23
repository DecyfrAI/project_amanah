import { describe, expect, it } from 'vitest';

import type { OverviewDay } from '@/api/contracts';

import { orderedSources, sourceLikelyHate } from './source-stack';

function day(
  date: string,
  sources: OverviewDay['sources'],
  likelyHate = sources.reduce((sum, source) => sum + source.likelyHate, 0),
): OverviewDay {
  return {
    date,
    collected: true,
    observed: 40,
    relevant: 20,
    likelyHate,
    nonRelevant: 20,
    sources,
  };
}

describe('orderedSources', () => {
  it('orders sources by total likely-hate across the window, largest first', () => {
    const days = [
      day('2026-08-01', [
        { key: 'reddit', label: 'Reddit', likelyHate: 2, relevant: 8 },
        { key: 'youtube', label: 'YouTube', likelyHate: 5, relevant: 12 },
      ]),
      day('2026-08-02', [
        { key: 'youtube', label: 'YouTube', likelyHate: 4, relevant: 10 },
        { key: 'reddit', label: 'Reddit', likelyHate: 1, relevant: 6 },
      ]),
    ];

    expect(orderedSources(days).map((source) => source.key)).toEqual(['youtube', 'reddit']);
  });

  it('ignores gap days when ranking sources', () => {
    const days: OverviewDay[] = [
      {
        date: '2026-08-07',
        collected: false,
        observed: null,
        relevant: null,
        likelyHate: null,
        nonRelevant: null,
        sources: [],
      },
      day('2026-08-08', [{ key: 'reddit', label: 'Reddit', likelyHate: 3, relevant: 7 }]),
    ];

    expect(orderedSources(days)).toEqual([{ key: 'reddit', label: 'Reddit', totalLikelyHate: 3 }]);
  });
});

describe('sourceLikelyHate', () => {
  it('returns zero when a source is missing from a collected day', () => {
    const collected = day('2026-08-01', [
      { key: 'youtube', label: 'YouTube', likelyHate: 4, relevant: 9 },
    ]);
    expect(sourceLikelyHate(collected, 'reddit')).toBe(0);
  });
});
