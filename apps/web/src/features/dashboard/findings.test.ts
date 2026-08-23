import { describe, expect, it } from 'vitest';

import type { OverviewBreakdown, OverviewDay, OverviewMetric } from '@/api';

import { findingFromBreakdownRow, findingFromDay, findingFromMetric } from './findings';

const collectedDay: OverviewDay = {
  date: '2026-08-16',
  collected: true,
  observed: 43,
  relevant: 31,
  likelyHate: 6,
  nonRelevant: 12,
  sources: [
    { key: 'youtube', label: 'YouTube', likelyHate: 4, relevant: 20 },
    { key: 'reddit', label: 'Reddit', likelyHate: 2, relevant: 11 },
  ],
};

const gapDay: OverviewDay = {
  date: '2026-08-07',
  collected: false,
  observed: null,
  relevant: null,
  likelyHate: null,
  nonRelevant: null,
  sources: [],
};

const breakdown: OverviewBreakdown = {
  id: 'by-type',
  label: 'By type',
  dimension: 'hate_type',
  definition: 'Share of items classified as likely hate.',
  total: 10,
  countLabel: 'items classified as likely hate',
  denominatorLabel: 'Muslim-related items',
  rows: [
    {
      key: 'threat',
      label: 'Threat or incitement',
      count: 4,
      denominator: 31,
      rate: 4 / 31,
    },
  ],
};

const rateMetric: OverviewMetric = {
  id: 'rate',
  label: 'Likely hate rate',
  definition: 'Likely-hate items divided by Muslim-related items.',
  unit: 'rate',
  value: 0.187,
  numerator: 253,
  denominator: 1350,
  isModelOnly: true,
  insufficientVolume: false,
  changeVsBaseline: null,
};

describe('findingFromDay', () => {
  it('freezes the same sentence the chart reads out', () => {
    const finding = findingFromDay(collectedDay, '/app/explorer?from=2026-08-16&to=2026-08-16', [
      'youtube',
    ]);

    expect(finding?.title).toBe('Likely-hate rate on 16 August');
    expect(finding?.claim).toMatch(/6 of 31/);
    expect(finding?.numerator).toBe(6);
    expect(finding?.denominator).toBe(31);
    expect(finding?.itemsObserved).toBe(43);
    expect(finding?.itemsRelevant).toBe(31);
  });

  it('refuses an uncollected day', () => {
    expect(findingFromDay(gapDay, '/app/explorer', ['youtube'])).toBeNull();
  });
});

describe('findingFromBreakdownRow', () => {
  it('keeps the row count and the window coverage separate', () => {
    const finding = findingFromBreakdownRow(
      breakdown,
      'threat',
      '2026-07-18',
      '2026-08-16',
      '/app/explorer?hate_type=threat',
      ['youtube'],
      5491,
      1350,
    );

    expect(finding?.numerator).toBe(4);
    expect(finding?.denominator).toBe(31);
    expect(finding?.itemsObserved).toBe(5491);
    expect(finding?.itemsRelevant).toBe(1350);
    expect(finding?.claim).toMatch(/4 of 10/);
  });

  it('refuses a key that is not on the figure', () => {
    expect(
      findingFromBreakdownRow(
        breakdown,
        'missing',
        '2026-07-18',
        '2026-08-16',
        '/app/explorer',
        ['youtube'],
        1,
        1,
      ),
    ).toBeNull();
  });
});

describe('findingFromMetric', () => {
  it('freezes a rate with both parts of the pair', () => {
    const finding = findingFromMetric(
      rateMetric,
      '2026-07-18',
      '2026-08-16',
      '/app/explorer',
      ['youtube'],
      5491,
      1350,
    );

    expect(finding?.title).toBe('Likely hate rate');
    expect(finding?.claim).toMatch(/18\.7%/);
    expect(finding?.numerator).toBe(253);
    expect(finding?.denominator).toBe(1350);
  });

  it('refuses a figure that cannot state a pair', () => {
    expect(
      findingFromMetric(
        { ...rateMetric, insufficientVolume: true },
        '2026-07-18',
        '2026-08-16',
        '/app/explorer',
        ['youtube'],
        5491,
        1350,
      ),
    ).toBeNull();
  });
});
