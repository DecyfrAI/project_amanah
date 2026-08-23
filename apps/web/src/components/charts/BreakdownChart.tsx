import type { OverviewBreakdown } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';

import { BarVisual, BubbleVisual, DonutVisual, LollipopVisual } from './BreakdownVisuals';
import { formatRate } from './rate';

import styles from './BreakdownChart.module.css';

interface BreakdownChartProps {
  breakdown: OverviewBreakdown;
  /**
   * Builds the drill-down for one row, or null where the dimension has no
   * matching filter to hand over.
   */
  buildHref: ((dimension: OverviewBreakdown['dimension'], key: string) => string) | null;
  /** Starts a snapshot insight on this row. Absent where creating is gated. */
  onReportRow?: ((key: string) => void) | undefined;
}

/**
 * One composition of the likely-hate items.
 *
 * The mark changes with the axis: a lollipop for many named types, discs for
 * severity, a ring where there are only two platforms, and bars for review
 * state. Every figure still carries the count, the share, and a table, because
 * a colour or an angle is never enough on its own.
 */
export function BreakdownChart({ breakdown, buildHref, onReportRow }: BreakdownChartProps) {
  return (
    <figure className={styles.figure}>
      <div className={styles.captionRow}>
        <figcaption className={styles.caption}>{breakdown.label}</figcaption>
        <InfoTip label={breakdown.label} placement="card">
          {breakdown.definition}
        </InfoTip>
      </div>

      {breakdown.dimension === 'hate_type' && (
        <LollipopVisual breakdown={breakdown} buildHref={buildHref} onReportRow={onReportRow} />
      )}
      {breakdown.dimension === 'severity' && (
        <BubbleVisual breakdown={breakdown} buildHref={buildHref} onReportRow={onReportRow} />
      )}
      {breakdown.dimension === 'platform' && (
        <DonutVisual breakdown={breakdown} buildHref={buildHref} onReportRow={onReportRow} />
      )}
      {breakdown.dimension === 'review_state' && (
        <BarVisual breakdown={breakdown} buildHref={buildHref} onReportRow={onReportRow} />
      )}

      <details className={styles.disclosure}>
        <summary className={styles.disclosureSummary}>Show {breakdown.label} as a table</summary>
        <table className={styles.table}>
          <caption className={styles.tableCaption}>
            {breakdown.label}, counting {breakdown.countLabel}, with each row&apos;s share of the
            total and its rate against {breakdown.denominatorLabel}.
          </caption>
          <thead>
            <tr>
              <th scope="col">Group</th>
              <th scope="col">Count</th>
              <th scope="col">Share of total</th>
              <th scope="col">Rate of {breakdown.denominatorLabel}</th>
            </tr>
          </thead>
          <tbody>
            {breakdown.rows.map((row) => (
              <tr key={row.key}>
                <th scope="row">{row.label}</th>
                <td>{row.count.toLocaleString('en-GB')}</td>
                <td>{formatRate(breakdown.total === 0 ? 0 : row.count / breakdown.total)}</td>
                <td>
                  {row.rate === null
                    ? `Too few items (${row.denominator.toLocaleString('en-GB')}) to state a rate`
                    : `${formatRate(row.rate)} of ${row.denominator.toLocaleString('en-GB')}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
