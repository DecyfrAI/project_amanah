import { Link } from 'react-router-dom';

import type { OverviewDay } from '@/api/contracts';
import { dayExplorerHref } from '@/features/dashboard/explorer-href';

import { dailyRate, formatDay, formatRate } from './rate';

import styles from './DailySeriesTable.module.css';

interface DailySeriesTableProps {
  days: readonly OverviewDay[];
  explorerPath?: string | null;
  explorerSearch?: string;
}

/**
 * The tabular equivalent of the chart, required for every chart in this product.
 *
 * A day with no collection says so in the row rather than showing 0, so the
 * table cannot be read as a quiet day either. A collected row can open Explorer
 * on that day.
 */
export function DailySeriesTable({
  days,
  explorerPath = null,
  explorerSearch = '',
}: DailySeriesTableProps) {
  return (
    <table className={styles.table}>
      <caption className={styles.caption}>
        Daily likely anti-Muslim hate rate, with the counts it rests on
      </caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Muslim-related</th>
          <th scope="col">Likely hate</th>
          <th scope="col">Rate</th>
        </tr>
      </thead>
      <tbody>
        {days.map((day) => {
          const rate = dailyRate(day);
          const href =
            explorerPath === null || !day.collected
              ? null
              : dayExplorerHref(explorerPath, explorerSearch, day.date);
          return (
            <tr key={day.date}>
              <th scope="row">
                {href === null ? (
                  formatDay(day.date)
                ) : (
                  <Link className={styles.rowLink} to={href}>
                    {formatDay(day.date)}
                    <span className="visually-hidden">, open records in Explorer</span>
                  </Link>
                )}
              </th>
              {day.collected ? (
                <>
                  <td>{day.relevant}</td>
                  <td>{day.likelyHate}</td>
                  <td>{formatRate(rate)}</td>
                </>
              ) : (
                <td className={styles.gap} colSpan={3}>
                  No collection on this day
                </td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
