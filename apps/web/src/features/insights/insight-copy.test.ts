import { describe, expect, it } from 'vitest';

import type { Insight } from '@/api';

import { insightKind, insightProvenance, insightSourceLine } from './insight-copy';

function insight(overrides: Partial<Insight> = {}): Insight {
  return {
    id: 'ins_test',
    title: 'A fixture finding',
    summary: 'A summary.',
    window: { from: '2026-08-01', to: '2026-08-16', timezone: 'UTC' },
    coverage: {
      sources: ['youtube'],
      itemsObserved: 10,
      itemsRelevant: 4,
      lastSuccessfulRun: null,
      warnings: [],
    },
    facts: [],
    citations: [],
    generation: {
      model: 'fixture',
      generatedAt: '2026-08-16T14:00:00Z',
      isMachineGenerated: true,
    },
    ...overrides,
  };
}

describe('insight-copy', () => {
  it('names sources the way the rest of the product does', () => {
    expect(insightSourceLine(insight())).toBe('YouTube');
    expect(insightSourceLine(insight({ coverage: { ...insight().coverage, sources: [] } }))).toBe(
      'No source recorded',
    );
  });

  it('labels generation without presenting a snapshot as a model finding', () => {
    expect(insightKind(insight()).label).toBe('Machine-generated');
    expect(
      insightKind(insight({ generation: { ...insight().generation, model: 'viewer-snapshot' } }))
        .label,
    ).toBe('Snapshot from a figure');
    expect(
      insightProvenance(
        insight({
          generation: {
            model: 'viewer-snapshot',
            generatedAt: '2026-08-16T14:00:00Z',
            isMachineGenerated: false,
          },
        }),
      ),
    ).toMatch(/started from a figure/i);
  });
});
