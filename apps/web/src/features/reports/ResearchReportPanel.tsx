import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';

import { ApiRequestError, type WireResearchReport } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';
import { useDashboardFilters } from '@/features/dashboard/useDashboardFilters';

import { useCreateResearchReport, useDownloadResearchReportCsv } from './useResearchReport';

import styles from './ResearchReportPanel.module.css';

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return fallback;
}

/**
 * Research-report snapshots (F-S16, completion guide step 7).
 *
 * Creation posts the dashboard filters to `POST /v1/research-reports`, which
 * freezes an immutable snapshot server-side. The panel then renders that stored
 * snapshot — its scope, coverage, metrics, findings, citations, methodology
 * version, and limitations — rather than a local illustration. Print styles let
 * the browser's own Save as PDF produce the report artifact.
 */
export function ResearchReportPanel() {
  const { filters } = useDashboardFilters();
  const create = useCreateResearchReport();
  const download = useDownloadResearchReportCsv();

  const [title, setTitle] = useState('');
  const [includeCsv, setIncludeCsv] = useState(true);
  const [titleError, setTitleError] = useState<string | null>(null);

  const handleTitle = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setTitle(event.currentTarget.value);
    setTitleError(null);
  }, []);

  const handleIncludeCsv = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setIncludeCsv(event.currentTarget.checked);
  }, []);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      const trimmed = title.trim();
      if (trimmed.length < 3) {
        setTitleError('Give the report a title of at least three characters.');
        return;
      }
      if (create.isPending) {
        return;
      }
      create.mutate({ title: trimmed, filters, includeAggregateCsv: includeCsv });
    },
    [create, filters, includeCsv, title],
  );

  const report = create.data;

  const handleDownload = useCallback((): void => {
    if (report !== undefined) {
      download.mutate(report);
    }
  }, [download, report]);

  const handlePrint = useCallback((): void => {
    window.print();
  }, []);

  return (
    <section className={styles.card} aria-labelledby="research-report-heading">
      <div className={styles.headingRow}>
        <h2 id="research-report-heading" className={styles.sectionHeading}>
          Research report
        </h2>
        <InfoTip label="Research report">
          A snapshot freezes the filters, coverage, and figures at the moment it is created, so the
          report cannot drift from the query behind it. It describes the monitored sample it names,
          never a whole platform.
        </InfoTip>
      </div>
      <p className={styles.lead}>
        Freeze the figures for the filters currently applied on Overview into an immutable snapshot.
        Aggregate counts and denominators only: no item-level rows leave through this export.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="report-title">
            Report title
          </label>
          <input
            className={styles.control}
            id="report-title"
            name="report-title"
            type="text"
            value={title}
            onChange={handleTitle}
            maxLength={200}
            aria-describedby="report-title-hint"
            aria-invalid={titleError !== null}
          />
          <p className={styles.hint} id="report-title-hint">
            Names the snapshot in your history. The scope below comes from the current filters.
          </p>
          {titleError !== null && (
            <p className={styles.error} role="alert">
              {titleError}
            </p>
          )}
        </div>

        <div className={styles.checkRow}>
          <input
            id="include-csv"
            name="include-csv"
            type="checkbox"
            checked={includeCsv}
            onChange={handleIncludeCsv}
          />
          <label className={styles.label} htmlFor="include-csv">
            Include an aggregate CSV
          </label>
        </div>

        <p className={styles.hint}>
          Scope: {filters.from ?? 'earliest collected'} to {filters.to ?? 'latest collected'}
          {(filters.platforms ?? []).length > 0 && `, ${(filters.platforms ?? []).join(', ')}`}.
        </p>

        <button type="submit" className={styles.primaryAction} disabled={create.isPending}>
          {create.isPending ? 'Freezing snapshot…' : 'Generate report'}
        </button>
        {create.isError && (
          <p className={styles.error} role="alert">
            {errorMessage(create.error, 'The report could not be created. Try again.')}
          </p>
        )}
      </form>

      {report !== undefined && (
        <ReportSnapshotView
          report={report}
          onDownload={handleDownload}
          onPrint={handlePrint}
          isDownloading={download.isPending}
          downloadError={
            download.isError
              ? errorMessage(download.error, 'The CSV could not be downloaded. Try again.')
              : null
          }
        />
      )}
    </section>
  );
}

interface ReportSnapshotViewProps {
  readonly report: WireResearchReport;
  readonly onDownload: () => void;
  readonly onPrint: () => void;
  readonly isDownloading: boolean;
  readonly downloadError: string | null;
}

function ReportSnapshotView({
  report,
  onDownload,
  onPrint,
  isDownloading,
  downloadError,
}: ReportSnapshotViewProps) {
  return (
    <article className={styles.snapshot} aria-labelledby={`${report.id}-title`}>
      <h3 className={styles.snapshotTitle} id={`${report.id}-title`}>
        {report.title}
      </h3>

      <dl className={styles.facts}>
        <div className={styles.fact}>
          <dt className={styles.term}>Window</dt>
          <dd className={styles.value}>
            {report.window_start.slice(0, 10)} to {report.window_end.slice(0, 10)}
          </dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Sources in scope</dt>
          <dd className={styles.value}>
            {report.source_scope.length === 0 ? 'None recorded' : report.source_scope.join(', ')}
          </dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Data mode</dt>
          <dd className={styles.value}>{report.data_mode}</dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Coverage</dt>
          <dd className={styles.value}>
            {report.coverage.last_success_at === null
              ? 'No successful collection recorded'
              : `Last successful run ${report.coverage.last_success_at.slice(0, 10)}`}
            {report.coverage.is_stale && ' · stale'}
          </dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Methodology version</dt>
          <dd className={styles.value}>{report.methodology_version}</dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Reference</dt>
          <dd className={styles.value}>{report.id}</dd>
        </div>
      </dl>

      <h4 className={styles.label}>Figures</h4>
      <dl className={styles.facts}>
        {report.metrics.map((metric) => (
          <div className={styles.fact} key={metric.key}>
            <dt className={styles.term}>{metric.key.replaceAll('_', ' ')}</dt>
            <dd className={styles.value}>
              {metric.value === null ? 'Not available in this window' : metric.value}
              {metric.numerator !== null &&
                metric.denominator !== null &&
                ` (${metric.numerator} of ${metric.denominator})`}
            </dd>
          </div>
        ))}
      </dl>

      {report.findings.length > 0 && (
        <>
          <h4 className={styles.label}>Findings</h4>
          <ul className={styles.list}>
            {report.findings.map((finding) => (
              <li key={finding.key}>{finding.statement}</li>
            ))}
          </ul>
        </>
      )}

      {report.citations.length > 0 && (
        <>
          <h4 className={styles.label}>Citations</h4>
          <ul className={styles.list}>
            {report.citations.map((citation) => (
              <li key={citation.id}>
                {citation.label} ({citation.kind})
              </li>
            ))}
          </ul>
        </>
      )}

      {report.limitations.length > 0 && (
        <>
          <h4 className={styles.label}>Limitations</h4>
          <ul className={styles.list}>
            {report.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        </>
      )}

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.action}
          onClick={onDownload}
          disabled={!report.aggregate_csv_available || isDownloading}
        >
          {isDownloading ? 'Preparing CSV…' : 'Download aggregate CSV'}
        </button>
        <button type="button" className={styles.action} onClick={onPrint}>
          Print or save as PDF
        </button>
      </div>
      {!report.aggregate_csv_available && (
        <p className={styles.pending}>
          This snapshot was created without an aggregate CSV. Create another with the CSV option
          selected to export one.
        </p>
      )}
      {downloadError !== null && (
        <p className={styles.error} role="alert">
          {downloadError}
        </p>
      )}
    </article>
  );
}
