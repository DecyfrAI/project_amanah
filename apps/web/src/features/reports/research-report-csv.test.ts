import { describe, expect, it } from 'vitest';

import type { ResearchReport } from '@/api';

import { csvFilename, renderAggregateCsv } from './research-report-csv';

function reportWith(overrides: Partial<ResearchReport> = {}): ResearchReport {
  return {
    id: 'rep_abc123',
    title: 'August monitored sample',
    filter_hash: 'a'.repeat(64),
    filters: {},
    data_version: '2026-08-09..2026-08-22',
    coverage: {
      last_success_at: '2026-08-22T09:30:00Z',
      coverage_score: 0.86,
      data_mode: 'fixture',
      is_stale: false,
      warnings: [],
    },
    metrics: [
      { key: 'observed_count', value: 1483, numerator: null, denominator: null },
      { key: 'likely_anti_muslim_rate', value: 0.187, numerator: 253, denominator: 1350 },
    ],
    findings: [],
    citations: [],
    methodology_version: 'fixture-2026.08',
    limitations: [],
    source_scope: ['youtube', 'news_web'],
    window_start: '2026-08-09',
    window_end: '2026-08-22',
    data_mode: 'fixture',
    redaction_mode: 'default_redacted',
    status: 'ready',
    aggregate_csv_available: true,
    created_at: '2026-08-22T10:00:00Z',
    completed_at: '2026-08-22T10:00:00Z',
    ...overrides,
  };
}

describe('renderAggregateCsv', () => {
  it('writes the same twelve columns the backend writes, in the same order', () => {
    const [header] = renderAggregateCsv(reportWith()).split('\n');

    expect(header).toBe(
      'metric_key,value,numerator,denominator,window_start,window_end,source_scope,coverage_score,data_version,methodology_version,data_mode,redaction_mode',
    );
  });

  it('carries each metric with its numerator and denominator', () => {
    const rows = renderAggregateCsv(reportWith()).trim().split('\n');

    expect(rows).toHaveLength(3);
    expect(rows[1]).toContain('observed_count,1483,,');
    expect(rows[2]).toContain('likely_anti_muslim_rate,0.187,253,1350');
  });

  it('joins the source scope with a pipe so it survives one CSV cell', () => {
    expect(renderAggregateCsv(reportWith())).toContain('youtube|news_web');
  });

  it('neutralises a cell a spreadsheet would execute as a formula', () => {
    // A source key beginning with `=` would otherwise run on open in Excel.
    const csv = renderAggregateCsv(reportWith({ source_scope: ['=cmd|/c calc'] }));

    expect(csv).toContain("'=cmd|/c calc");
    expect(csv).not.toMatch(/,=cmd/);
  });

  it('quotes a value containing a comma rather than splitting the row', () => {
    const csv = renderAggregateCsv(reportWith({ data_version: 'a,b' }));

    expect(csv).toContain('"a,b"');
  });

  it('writes an empty cell for an absent numerator, never a zero', () => {
    const csv = renderAggregateCsv(reportWith());

    // observed_count has no denominator; a 0 there would read as a real count.
    expect(csv).not.toContain('observed_count,1483,0,0');
  });

  it('names the file after the window and the filter hash', () => {
    expect(csvFilename(reportWith())).toBe('amanah-report-2026-08-09-to-2026-08-22-aaaaaaaa.csv');
  });
});
