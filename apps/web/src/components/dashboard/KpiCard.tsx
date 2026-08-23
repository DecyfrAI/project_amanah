import { Link } from 'react-router-dom';

import type { OverviewMetric } from '@/api/contracts';
import { InfoTip } from '@/components/ui/InfoTip';

import styles from './KpiCard.module.css';

interface KpiCardProps {
  metric: OverviewMetric;
  /** Starts a snapshot insight on this figure. Absent where creating is gated. */
  onReport?: (() => void) | undefined;
  /** Opens the Explorer on the same window the figure describes. */
  explorerHref?: string | null;
}

function formatValue(metric: OverviewMetric): string {
  if (metric.insufficientVolume || metric.value === null) {
    return 'Insufficient volume';
  }
  if (metric.unit === 'rate') {
    return `${(metric.value * 100).toFixed(1)}%`;
  }
  return metric.value.toLocaleString('en');
}

function formatChange(metric: OverviewMetric): string | null {
  const change = metric.changeVsBaseline;
  if (change === null) {
    return null;
  }

  const direction = change.absolute > 0 ? 'Up' : change.absolute < 0 ? 'Down' : 'Level with';
  if (change.absolute === 0) {
    return `Level with the ${change.baselineLabel}`;
  }

  const size =
    metric.unit === 'rate'
      ? `${Math.abs(change.absolute * 100).toFixed(1)} percentage points`
      : `${Math.abs(change.absolute).toLocaleString('en')}`;

  return `${direction} ${size} against the ${change.baselineLabel}`;
}

/**
 * One KPI, with the things that make it readable rather than just large.
 *
 * The value never appears without its denominator, and a model-only figure says
 * so on the card in words, not by a colour a reader has to learn. Direction of
 * change is stated in text, so it does not depend on an arrow or on green
 * meaning good, which it would not here.
 */
export function KpiCard({ metric, onReport, explorerHref = null }: KpiCardProps) {
  const change = formatChange(metric);
  const definitionId = `${metric.id}-definition`;

  return (
    <article className={styles.card} aria-labelledby={`${metric.id}-label`}>
      <div className={styles.labelRow}>
        <h3 id={`${metric.id}-label`} className={styles.label}>
          {metric.label}
        </h3>
        <InfoTip label={metric.label} placement="card">
          <span id={definitionId}>{metric.definition}</span>
        </InfoTip>
      </div>

      {explorerHref !== null ? (
        <Link
          className={styles.valueLink}
          to={explorerHref}
          aria-label={`${formatValue(metric)}, open ${metric.label} in Explorer`}
          aria-describedby={definitionId}
        >
          <span className={styles.value}>{formatValue(metric)}</span>
        </Link>
      ) : (
        <p className={styles.value} aria-describedby={definitionId}>
          {formatValue(metric)}
        </p>
      )}

      {metric.numerator !== null && metric.denominator !== null && (
        <p className={styles.ratio}>
          {metric.numerator.toLocaleString('en')} of {metric.denominator.toLocaleString('en')}
        </p>
      )}

      {change !== null && <p className={styles.change}>{change}</p>}

      {metric.isModelOnly && (
        <p className={styles.provenance}>
          <span className={styles.provenanceIcon} aria-hidden="true">
            <ModelIcon />
          </span>
          Model classification, not yet reviewed
        </p>
      )}

      <div className={styles.actions}>
        {explorerHref !== null && (
          <Link className={styles.drillDown} to={explorerHref}>
            Open in Explorer
          </Link>
        )}
        {onReport !== undefined && (
          <button type="button" className={styles.report} onClick={onReport}>
            Start insight on {metric.label}
          </button>
        )}
      </div>
    </article>
  );
}

function ModelIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <rect x="5" y="7" width="14" height="12" rx="2" />
      <path d="M9 4v3M15 4v3M9.5 12h.5M14 12h.5M9.5 15.5h5" />
    </svg>
  );
}
