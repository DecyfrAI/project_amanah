import type { DateWindow, OverviewCoverage } from '@/api/contracts';
import { InfoTip } from '@/components/ui/InfoTip';

import styles from './CoverageStrip.module.css';

interface CoverageStripProps {
  window: DateWindow;
  coverage: OverviewCoverage;
}

const SOURCE_NAMES: Record<string, string> = {
  youtube: 'YouTube',
  reddit: 'Reddit',
};

function sourceName(source: string): string {
  return SOURCE_NAMES[source] ?? source;
}

function formatRun(timestamp: string | null): string {
  if (timestamp === null) {
    return 'No successful run recorded';
  }
  return new Date(timestamp).toISOString().replace('T', ' ').slice(0, 16).concat(' UTC');
}

/**
 * The scope statement every figure below it depends on.
 *
 * It sits above the KPIs rather than in a footnote because the numbers are
 * meaningless without it: the same count means different things across 22
 * videos and across 200. Warnings are part of the strip, not a dismissible
 * toast, since a failed collection run is the most common reason a chart looks
 * calmer than reality.
 */
export function CoverageStrip({ window, coverage }: CoverageStripProps) {
  return (
    <section className={styles.strip} aria-labelledby="coverage-heading">
      <div className={styles.headingRow}>
        <h2 id="coverage-heading" className={styles.heading}>
          What this view covers
        </h2>
        <InfoTip label="What this view covers">
          The window, sources, and collection coverage every figure below depends on. A failed day
          is a gap, not a quiet day drawn as zero.
        </InfoTip>
      </div>

      <dl className={styles.items}>
        <div className={styles.item}>
          <dt className={styles.term}>Window</dt>
          <dd className={styles.value}>
            {window.from} to {window.to} ({window.timezone})
          </dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.term}>Sources</dt>
          <dd className={styles.value}>{coverage.sources.map(sourceName).join(', ')}</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.term}>Monitored</dt>
          <dd className={styles.value}>
            {coverage.containersMonitored} {coverage.containerLabel}
          </dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.term}>Items collected</dt>
          <dd className={styles.value}>{coverage.itemsObserved.toLocaleString('en')}</dd>
        </div>
        <div className={styles.item}>
          <dt className={styles.term}>Last successful run</dt>
          <dd className={styles.value}>{formatRun(coverage.lastSuccessfulRun)}</dd>
        </div>
      </dl>

      {coverage.warnings.length > 0 && (
        <div className={styles.warnings}>
          <p className={styles.warningLabel}>
            <span className={styles.warningIcon} aria-hidden="true">
              <WarningIcon />
            </span>
            Coverage warning
          </p>
          <ul className={styles.warningList}>
            {coverage.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <p className={styles.caveat}>
        These figures describe this monitored sample only. They are not a measurement of a whole
        platform, a country, or any group of people.
      </p>
    </section>
  );
}

function WarningIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={24}
      height={24}
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M12 4.5 21 19.5H3Z" />
      <path d="M12 10v4M12 16.5v.5" />
    </svg>
  );
}
