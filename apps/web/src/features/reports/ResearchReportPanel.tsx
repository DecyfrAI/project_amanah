import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';

import { ApiRequestError, type ResearchReport } from '@/api';
import { Button } from '@/components/ui/Button';
import { InfoTip } from '@/components/ui/InfoTip';
import { useDashboardFilters } from '@/features/dashboard/useDashboardFilters';

import { downloadText } from './report-export';
import { csvFilename, renderAggregateCsv } from './research-report-csv';
import { useCreateResearchReport, useDownloadReportCsv } from './useResearchReport';

import styles from './ResearchReportPanel.module.css';

const METRIC_LABELS: Record<string, string> = {
  observed_count: 'Items collected',
  muslim_related_count: 'Muslim-related items',
  likely_anti_muslim_count: 'Classified as likely hate',
  reviewed_count: 'Confirmed by review',
  likely_anti_muslim_rate: 'Likely hate rate',
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The report could not be generated. Try again.';
}

function formatValue(metric: ResearchReport['metrics'][number]): string {
  if (metric.value === null) {
    return 'Not available';
  }
  if (metric.key === 'likely_anti_muslim_rate') {
    return `${(metric.value * 100).toFixed(1)}%`;
  }
  return metric.value.toLocaleString();
}

function formatBasis(metric: ResearchReport['metrics'][number]): string | null {
  if (metric.numerator === null || metric.denominator === null) {
    return null;
  }
  return `${metric.numerator.toLocaleString()} of ${metric.denominator.toLocaleString()}`;
}

/**
 * Generate an immutable research snapshot and export it.
 *
 * The scope is the filters already in the address bar, so a report describes the
 * sample the reader was looking at rather than one re-chosen in a second form
 * that could drift from it. Once frozen, the figures shown here are the stored
 * ones: this panel never re-queries to refresh them.
 */
export function ResearchReportPanel() {
  const { filters } = useDashboardFilters();
  const create = useCreateResearchReport();
  const download = useDownloadReportCsv();
  const [title, setTitle] = useState('');
  const [report, setReport] = useState<ResearchReport | null>(null);

  const handleTitleChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setTitle(event.currentTarget.value);
  }, []);

  const handleGenerate = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      const trimmed = title.trim();
      if (trimmed.length < 3) {
        return;
      }
      create.mutate(
        {
          title: trimmed,
          filters: {
            ...(filters.from === undefined ? {} : { date_from: filters.from }),
            ...(filters.to === undefined ? {} : { date_to: filters.to }),
            ...(filters.platforms === undefined || filters.platforms.length === 0
              ? {}
              : { platforms: [...filters.platforms] }),
            ...(filters.severityBands === undefined || filters.severityBands.length === 0
              ? {}
              : { severities: [...filters.severityBands] }),
            ...(filters.reviewStates === undefined || filters.reviewStates.length === 0
              ? {}
              : { review_states: [...filters.reviewStates] }),
          },
          metrics: [
            'observed_count',
            'muslim_related_count',
            'likely_anti_muslim_count',
            'reviewed_count',
            'likely_anti_muslim_rate',
          ],
          findings: ['monitored_sample_rate', 'analysis_coverage'],
          include_aggregate_csv: true,
          redaction_mode: 'default_redacted',
        },
        { onSuccess: setReport },
      );
    },
    [create, filters, title],
  );

  const handleDownloadCsv = useCallback((): void => {
    if (report === null) {
      return;
    }
    download.mutate(report, {
      onSuccess: (csv) => {
        downloadText(csvFilename(report), csv, 'text/csv;charset=utf-8');
      },
      onError: () => {
        // The stored snapshot is already in hand, so a transport failure does
        // not have to cost the reader their export.
        downloadText(csvFilename(report), renderAggregateCsv(report), 'text/csv;charset=utf-8');
      },
    });
  }, [download, report]);

  const handlePrint = useCallback((): void => {
    window.print();
  }, []);

  const handleReset = useCallback((): void => {
    setReport(null);
    setTitle('');
    create.reset();
    download.reset();
  }, [create, download]);

  const hateTypeNote =
    (filters.hateTypes?.length ?? 0) > 0
      ? 'A hate-type selection is active on screen but is not carried into the snapshot: a report can only freeze a scope the service can reproduce.'
      : null;

  return (
    <section className={styles.panel} aria-labelledby="research-report-heading">
      <div className={styles.headingRow}>
        <h2 id="research-report-heading" className={styles.heading}>
          Research report
        </h2>
        <InfoTip label="Research report">
          A frozen claim about a bounded sample. Aggregate only: counts and their denominators,
          never an item.
        </InfoTip>
      </div>

      {report === null ? (
        <form className={styles.form} onSubmit={handleGenerate}>
          <p className={styles.lead}>
            Freezes the figures for the filters currently applied. Change the window or the filters
            on Overview first; this report describes whatever scope is in the address bar when you
            generate it.
          </p>

          <dl className={styles.scope}>
            <div className={styles.scopeRow}>
              <dt className={styles.term}>Window</dt>
              <dd className={styles.value}>
                {filters.from ?? 'default start'} to {filters.to ?? 'default end'}
              </dd>
            </div>
            <div className={styles.scopeRow}>
              <dt className={styles.term}>Platforms</dt>
              <dd className={styles.value}>
                {(filters.platforms?.length ?? 0) === 0
                  ? 'All configured platforms'
                  : filters.platforms?.join(', ')}
              </dd>
            </div>
            <div className={styles.scopeRow}>
              <dt className={styles.term}>Severity</dt>
              <dd className={styles.value}>
                {(filters.severityBands?.length ?? 0) === 0
                  ? 'All bands'
                  : filters.severityBands?.join(', ')}
              </dd>
            </div>
            <div className={styles.scopeRow}>
              <dt className={styles.term}>Review state</dt>
              <dd className={styles.value}>
                {(filters.reviewStates?.length ?? 0) === 0
                  ? 'All states'
                  : filters.reviewStates?.join(', ')}
              </dd>
            </div>
          </dl>

          {hateTypeNote !== null && <p className={styles.note}>{hateTypeNote}</p>}

          <div className={styles.field}>
            <label className={styles.label} htmlFor="report-title">
              Report title
            </label>
            <input
              id="report-title"
              className={styles.control}
              value={title}
              onChange={handleTitleChange}
              minLength={3}
              maxLength={200}
              placeholder="Anti-Muslim hate in the monitored sample, August 2026"
              required
            />
          </div>

          {create.isError && (
            <p className={styles.error} role="alert">
              {errorMessage(create.error)}
            </p>
          )}

          <Button variant="primary" type="submit" disabled={create.isPending}>
            {create.isPending ? 'Freezing figures…' : 'Generate report'}
          </Button>
        </form>
      ) : (
        <div className={styles.result}>
          <div className={styles.resultHead}>
            <h3 className={styles.resultTitle}>{report.title}</h3>
            <button type="button" className={styles.reset} onClick={handleReset}>
              New report
            </button>
          </div>

          <p className={styles.frozen}>
            Frozen {new Date(report.completed_at).toLocaleString()}. Reference{' '}
            <span className={styles.mono}>{report.filter_hash.slice(0, 12)}</span>. These figures do
            not change when the data behind them does.
          </p>

          <dl className={styles.scope}>
            <div className={styles.scopeRow}>
              <dt className={styles.term}>Window frozen</dt>
              <dd className={styles.value}>
                {report.window_start} to {report.window_end}
              </dd>
            </div>
            <div className={styles.scopeRow}>
              <dt className={styles.term}>Sources</dt>
              <dd className={styles.value}>
                {report.source_scope.length === 0
                  ? 'None recorded'
                  : report.source_scope.join(', ')}
              </dd>
            </div>
          </dl>

          {(report.window_start !== (filters.from ?? report.window_start) ||
            report.window_end !== (filters.to ?? report.window_end)) && (
            <p className={styles.note}>
              The frozen window is narrower than the one requested, because collection does not
              cover the whole range. The report describes the days that exist, not the days asked
              for.
            </p>
          )}

          <ul className={styles.metrics}>
            {report.metrics.map((metric) => (
              <li key={metric.key} className={styles.metric}>
                <p className={styles.metricLabel}>{METRIC_LABELS[metric.key] ?? metric.key}</p>
                <p className={styles.metricValue}>{formatValue(metric)}</p>
                {formatBasis(metric) !== null && (
                  <p className={styles.metricBasis}>{formatBasis(metric)}</p>
                )}
              </li>
            ))}
          </ul>

          <ul className={styles.findings}>
            {report.findings.map((finding) => (
              <li key={finding.key} className={styles.finding}>
                {finding.statement}
              </li>
            ))}
          </ul>

          <section className={styles.limits} aria-labelledby="report-limits-heading">
            <h4 id="report-limits-heading" className={styles.limitsHeading}>
              Limitations
            </h4>
            <ul className={styles.limitList}>
              {report.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </section>

          <div className={styles.actions}>
            <Button variant="primary" type="button" onClick={handleDownloadCsv}>
              {download.isPending ? 'Preparing CSV…' : 'Download aggregate CSV'}
            </Button>
            <button type="button" className={styles.action} onClick={handlePrint}>
              Print or save as PDF
            </button>
          </div>
          <p className={styles.exportNote}>
            The CSV contains the aggregate counts and denominators shown in this report. It does not
            include item-level content or personal identifiers.
          </p>
        </div>
      )}
    </section>
  );
}
