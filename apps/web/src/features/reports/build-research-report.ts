/**
 * Fixture-mode research-report snapshot.
 *
 * Mirrors `ResearchReportService.create` server-side: the same metric keys, the
 * same two findings, the same citation shape. The figures are read from the
 * Overview the reader was already looking at, so a report and the dashboard it
 * was generated from can never disagree.
 *
 * A snapshot is frozen at creation. Nothing here re-queries later.
 */
import type {
  CreateResearchReportRequest,
  Overview,
  ReportFindingSnapshot,
  ReportMetricKey,
  ReportMetricSnapshot,
  ResearchReport,
} from '@/api';

/** Overview metric id backing each report metric key. */
const METRIC_SOURCE: Record<ReportMetricKey, string> = {
  observed_count: 'observed',
  muslim_related_count: 'relevant',
  likely_anti_muslim_count: 'likely-hate',
  reviewed_count: 'reviewed',
  likely_anti_muslim_rate: 'rate',
};

/**
 * SHA-256 of the canonical filters, matching the server's `_filter_hash`.
 *
 * Sorted keys and separator-free JSON so the same scope hashes identically in
 * both modes; a report generated in fixture mode can be recognised as the same
 * scope by the live service.
 */
async function filterHash(filters: CreateResearchReportRequest['filters']): Promise<string> {
  const canonical = JSON.stringify(filters, Object.keys(filters).toSorted());
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

function metricSnapshot(key: ReportMetricKey, overview: Overview): ReportMetricSnapshot {
  const source = overview.metrics.find((metric) => metric.id === METRIC_SOURCE[key]);
  return {
    key,
    value: source?.value ?? null,
    numerator: source?.numerator ?? null,
    denominator: source?.denominator ?? null,
  };
}

function findings(
  selected: readonly CreateResearchReportRequest['findings'][number][],
  overview: Overview,
  citationId: string,
): ReportFindingSnapshot[] {
  const rate = overview.metrics.find((metric) => metric.id === 'rate');
  const observed = overview.metrics.find((metric) => metric.id === 'observed');
  const numerator = rate?.numerator ?? 0;
  const denominator = rate?.denominator ?? 0;

  const statements: Record<CreateResearchReportRequest['findings'][number], string> = {
    monitored_sample_rate:
      denominator === 0
        ? 'No monitored-sample rate is available because the selected window contains no Muslim-related denominator.'
        : `The selected monitored sample contains ${String(numerator)} likely anti-Muslim items among ${String(denominator)} Muslim-related items.`,
    analysis_coverage: `Analysis coverage is based on ${String(overview.coverage.itemsRelevant)} analysed records among ${String(observed?.value ?? overview.coverage.itemsObserved)} observed records in the selected sample.`,
  };

  return selected.map((key) => ({
    key,
    statement: statements[key],
    citation_ids: [citationId],
  }));
}

const METHODOLOGY_VERSION = 'fixture-2026.08';

const LIMITATIONS: readonly string[] = [
  'Every figure describes the monitored sample named in this report. It is not a prevalence estimate for any platform.',
  'Classifications are model proposals awaiting review, not confirmed findings.',
  'Days with no successful collection run are excluded from denominators rather than counted as zero.',
];

export async function buildResearchReport(
  request: CreateResearchReportRequest,
  overview: Overview,
  dataMode: ResearchReport['data_mode'] = 'fixture',
): Promise<ResearchReport> {
  const hash = await filterHash(request.filters);
  const moment = new Date().toISOString();
  const dataVersion = `${overview.applied.from}..${overview.applied.to}`;
  const aggregateCitationId = `aggregate:${hash.slice(0, 16)}:${dataVersion}`;
  const methodologyCitationId = `methodology:${METHODOLOGY_VERSION}`;

  return {
    id: `rep_${hash.slice(0, 12)}`,
    title: request.title,
    filter_hash: hash,
    filters: request.filters,
    data_version: dataVersion,
    coverage: {
      last_success_at: overview.coverage.lastSuccessfulRun,
      coverage_score: null,
      data_mode: dataMode,
      is_stale: false,
      warnings: [...overview.coverage.warnings],
    },
    metrics: request.metrics.map((key) => metricSnapshot(key, overview)),
    findings: findings(request.findings, overview, aggregateCitationId),
    citations: [
      {
        id: aggregateCitationId,
        kind: 'aggregate',
        label: "Frozen deterministic aggregates for this report's exact filters.",
      },
      {
        id: methodologyCitationId,
        kind: 'methodology',
        label: 'Versioned Project Amanah methodology and limitations.',
      },
    ],
    methodology_version: METHODOLOGY_VERSION,
    limitations: [...LIMITATIONS],
    source_scope: [...overview.coverage.sources],
    window_start: overview.applied.from,
    window_end: overview.applied.to,
    data_mode: dataMode,
    redaction_mode: request.redaction_mode,
    status: 'ready',
    aggregate_csv_available: request.include_aggregate_csv,
    created_at: moment,
    completed_at: moment,
  };
}
