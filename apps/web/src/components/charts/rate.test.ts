import { describe, expect, it } from 'vitest';

import type { OverviewDay } from '@/api/contracts';

import { dailyRate, formatRate } from './rate';

function day(overrides: Partial<OverviewDay>): OverviewDay {
  return {
    date: '2026-08-01',
    collected: true,
    observed: 90,
    relevant: 20,
    likelyHate: 5,
    nonRelevant: 70,
    sources: [],
    ...overrides,
  };
}

describe('dailyRate', () => {
  it('divides likely hate by relevant items', () => {
    expect(dailyRate(day({ relevant: 20, likelyHate: 5 }))).toBeCloseTo(0.25);
  });

  it('returns null for an uncollected day rather than zero', () => {
    const uncollected = day({ collected: false, relevant: null, likelyHate: null });

    expect(dailyRate(uncollected)).toBeNull();
    expect(dailyRate(uncollected)).not.toBe(0);
  });

  it('returns null when there is no relevant sample to divide by', () => {
    expect(dailyRate(day({ relevant: 0, likelyHate: 0 }))).toBeNull();
  });

  it('reports a missing rate in words', () => {
    expect(formatRate(null)).toBe('No rate');
    expect(formatRate(0.2372)).toBe('23.7%');
  });
});
