/**
 * Aggregate CSV for a research-report snapshot.
 *
 * Mirrors `_render_aggregate_csv` in
 * `backend/src/amanah/reporting/research_reports.py` column for column, so the
 * file a reader gets is the same in fixture and live mode. Live mode downloads
 * the server's rendering; fixture mode renders here. If the backend columns
 * change, this changes with them.
 *
 * Aggregate only, by construction: the snapshot has no item to leak.
 */
import type { ResearchReport } from '@/api';

const COLUMNS = [
  'metric_key',
  'value',
  'numerator',
  'denominator',
  'window_start',
  'window_end',
  'source_scope',
  'coverage_score',
  'data_version',
  'methodology_version',
  'data_mode',
  'redaction_mode',
] as const;

/**
 * Neutralises a cell a spreadsheet would evaluate as a formula.
 *
 * A leading `=`, `+`, `-`, or `@` makes Excel and Sheets execute the cell, which
 * turns an exported report into an attack on whoever opens it. Prefixing an
 * apostrophe forces it back to text. Same guard as `_safe_csv_cell` server-side.
 */
function safeCell(value: string): string {
  return /^[=+\-@]/.test(value) ? `'${value}` : value;
}

/** RFC 4180 quoting: double the quotes, wrap anything that could break a row. */
function quote(value: string): string {
  const safe = safeCell(value);
  if (/[",\r\n]/.test(safe)) {
    return `"${safe.replaceAll('"', '""')}"`;
  }
  return safe;
}

function cell(value: string | number | null): string {
  if (value === null) {
    return '';
  }
  return quote(String(value));
}

export function renderAggregateCsv(report: ResearchReport): string {
  const rows = report.metrics.map((metric) =>
    [
      cell(metric.key),
      cell(metric.value),
      cell(metric.numerator),
      cell(metric.denominator),
      cell(report.window_start),
      cell(report.window_end),
      cell(report.source_scope.join('|')),
      cell(report.coverage.coverage_score),
      cell(report.data_version),
      cell(report.methodology_version),
      cell(report.data_mode),
      cell(report.redaction_mode),
    ].join(','),
  );

  return [COLUMNS.join(','), ...rows].join('\n') + '\n';
}

/** Stable, filesystem-safe name carrying the scope the file describes. */
export function csvFilename(report: ResearchReport): string {
  return `amanah-report-${report.window_start.slice(0, 10)}-to-${report.window_end.slice(0, 10)}-${report.filter_hash.slice(0, 8)}.csv`;
}
