import { useCallback, useState, type SyntheticEvent } from 'react';

import styles from './DashboardPreview.module.css';

/**
 * Synthetic daily figures for the marketing preview.
 *
 * Illustrative, not a reading. Every day carries both its numerator and its
 * denominator so the rate is never shown without the counts under it, and the
 * window is deliberately complete: coverage is stated rather than assumed.
 *
 * Totals reconcile with the fixture insight, 74 likely-hate items of 312
 * relevant items.
 */
interface Day {
  readonly date: string;
  /** Muslim-relevant items collected that day. The rate's denominator. */
  readonly relevant: number;
  /** Items classified as likely anti-Muslim hate, before review. */
  readonly likely: number;
}

/** Typed as non-empty so the first and last day need no undefined handling. */
const DAYS: readonly [Day, ...Day[]] = [
  { date: '9 Aug', relevant: 40, likely: 6 },
  { date: '10 Aug', relevant: 38, likely: 7 },
  { date: '11 Aug', relevant: 42, likely: 8 },
  { date: '12 Aug', relevant: 39, likely: 9 },
  { date: '13 Aug', relevant: 37, likely: 10 },
  { date: '14 Aug', relevant: 41, likely: 11 },
  { date: '15 Aug', relevant: 36, likely: 11 },
  { date: '16 Aug', relevant: 39, likely: 12 },
];

const TOTAL_RELEVANT = DAYS.reduce((total, day) => total + day.relevant, 0);
const TOTAL_LIKELY = DAYS.reduce((total, day) => total + day.likely, 0);

const CHART = {
  width: 560,
  height: 220,
  left: 44,
  right: 16,
  top: 16,
  bottom: 36,
} as const;

type MetricId = 'rate' | 'volume';

interface Metric {
  readonly id: MetricId;
  /** Text on the toggle. */
  readonly label: string;
  /** Chart title while this metric is shown. */
  readonly title: string;
  readonly value: (day: Day) => number;
}

const RATE_METRIC: Metric = {
  id: 'rate',
  label: 'Rate',
  title: 'Likely-hate rate among relevant items',
  value: (day) => day.likely / day.relevant,
};

const VOLUME_METRIC: Metric = {
  id: 'volume',
  label: 'Volume',
  title: 'Relevant items collected each day',
  value: (day) => day.relevant,
};

const METRICS: readonly Metric[] = [RATE_METRIC, VOLUME_METRIC];

function ratePercent(day: Day): string {
  return ((day.likely / day.relevant) * 100).toFixed(1);
}

/** Scale each metric to its own values, padded so the line never touches an edge. */
function domainOf(metric: Metric): { min: number; max: number } {
  const values = DAYS.map((day) => metric.value(day));
  const low = Math.min(...values);
  const high = Math.max(...values);
  const padding = (high - low) * 0.35;
  return { min: low - padding, max: high + padding };
}

interface Plot {
  readonly date: string;
  readonly cx: number;
  readonly cy: number;
}

interface Geometry {
  readonly linePoints: string;
  readonly plots: readonly Plot[];
}

/**
 * Both series are static, so their coordinates are computed once at module load
 * rather than on every render or on every toggle.
 */
function geometryOf(metric: Metric): Geometry {
  const { min, max } = domainOf(metric);
  const innerWidth = CHART.width - CHART.left - CHART.right;
  const innerHeight = CHART.height - CHART.top - CHART.bottom;
  const lastIndex = DAYS.length - 1;

  const plots = DAYS.map((day, index) => ({
    date: day.date,
    cx: CHART.left + (innerWidth * index) / lastIndex,
    cy: CHART.top + innerHeight * (1 - (metric.value(day) - min) / (max - min)),
  }));

  return {
    linePoints: plots.map((plot) => `${plot.cx.toFixed(1)},${plot.cy.toFixed(1)}`).join(' '),
    plots,
  };
}

const GEOMETRY: Readonly<Record<MetricId, Geometry>> = {
  rate: geometryOf(RATE_METRIC),
  volume: geometryOf(VOLUME_METRIC),
};

const FIRST_DAY = DAYS[0];
const LAST_DAY = DAYS.at(-1) ?? DAYS[0];
const AVERAGE_PERCENT = ((TOTAL_LIKELY / TOTAL_RELEVANT) * 100).toFixed(1);

const SUMMARY =
  `Fixture preview of the Overview chart, ${FIRST_DAY.date} to ${LAST_DAY.date}. ` +
  `Among relevant items, the likely-hate rate rises from ${ratePercent(FIRST_DAY)} percent to ` +
  `${ratePercent(LAST_DAY)} percent, ${TOTAL_LIKELY} of ${TOTAL_RELEVANT} across the window. ` +
  'Between 36 and 42 relevant items were collected each day, with no missing collection days. ' +
  'The same figures are available as a table below.';

export function DashboardPreview() {
  const [metricId, setMetricId] = useState<MetricId>('rate');
  const [selectedDate, setSelectedDate] = useState(LAST_DAY.date);

  // One handler for the whole group, reading its target's own data attribute,
  // so no per-button closure is created during render.
  const handleMetricSelect = useCallback((event: SyntheticEvent<HTMLButtonElement>): void => {
    const next = event.currentTarget.dataset.metric;
    if (next === 'rate' || next === 'volume') {
      setMetricId(next);
    }
  }, []);

  const handleDaySelect = useCallback((event: SyntheticEvent<HTMLButtonElement>): void => {
    const next = event.currentTarget.dataset.date;
    if (next !== undefined) {
      setSelectedDate(next);
    }
  }, []);

  const metric = metricId === 'volume' ? VOLUME_METRIC : RATE_METRIC;
  const geometry = GEOMETRY[metricId];
  const selectedDay: Day = DAYS.find((day) => day.date === selectedDate) ?? LAST_DAY;
  const selectedPlot = geometry.plots.find((plot) => plot.date === selectedDate);

  return (
    <figure className={styles.preview}>
      <figcaption className={styles.caption}>
        <p className={styles.kicker}>Overview preview</p>
        <p className={styles.title}>{metric.title}</p>
        <p className={styles.kpi}>
          {TOTAL_LIKELY} of {TOTAL_RELEVANT}
          <span className={styles.kpiHint}>
            {AVERAGE_PERCENT} percent across the window, fixture sample
          </span>
        </p>
      </figcaption>

      <fieldset className={styles.toggle}>
        <legend className="visually-hidden">Chart metric</legend>
        {METRICS.map((candidate) => (
          <button
            key={candidate.id}
            type="button"
            className={styles.toggleButton}
            data-metric={candidate.id}
            aria-pressed={candidate.id === metricId}
            onClick={handleMetricSelect}
          >
            {candidate.label}
          </button>
        ))}
      </fieldset>

      <p className="visually-hidden">{SUMMARY}</p>

      <svg
        className={styles.chart}
        viewBox={`0 0 ${CHART.width} ${CHART.height}`}
        aria-hidden="true"
      >
        <line
          className={styles.grid}
          x1={CHART.left}
          y1={CHART.top}
          x2={CHART.left}
          y2={CHART.height - CHART.bottom}
        />
        <line
          className={styles.grid}
          x1={CHART.left}
          y1={CHART.height - CHART.bottom}
          x2={CHART.width - CHART.right}
          y2={CHART.height - CHART.bottom}
        />
        <polyline className={styles.line} points={geometry.linePoints} />
        {geometry.plots.map((plot) => (
          <circle key={plot.date} className={styles.point} cx={plot.cx} cy={plot.cy} />
        ))}
        {selectedPlot !== undefined && (
          <>
            <line
              className={styles.marker}
              x1={selectedPlot.cx}
              y1={CHART.top}
              x2={selectedPlot.cx}
              y2={CHART.height - CHART.bottom}
            />
            <circle className={styles.highlight} cx={selectedPlot.cx} cy={selectedPlot.cy} />
          </>
        )}
        <text className={styles.axis} x={CHART.left} y={CHART.height - 10}>
          {FIRST_DAY.date}
        </text>
        <text className={styles.axis} x={CHART.width - CHART.right - 36} y={CHART.height - 10}>
          {LAST_DAY.date}
        </text>
      </svg>

      <fieldset className={styles.days}>
        <legend className="visually-hidden">Select a day</legend>
        {DAYS.map((day) => (
          <button
            key={day.date}
            type="button"
            className={styles.dayButton}
            data-date={day.date}
            aria-pressed={day.date === selectedDate}
            onClick={handleDaySelect}
            onFocus={handleDaySelect}
            onMouseEnter={handleDaySelect}
          >
            {day.date}
          </button>
        ))}
      </fieldset>

      <p className={styles.readout} aria-live="polite">
        <span className={styles.readoutDate}>{selectedDay.date}</span>
        {selectedDay.likely} of {selectedDay.relevant} relevant items classified as likely hate,{' '}
        {ratePercent(selectedDay)} percent
      </p>

      <p className={styles.note}>
        Coverage: {DAYS.length} of {DAYS.length} collection days ran in this window, so the line is
        continuous. A day that failed to collect would break the line, never read as zero.
      </p>

      <details className={styles.disclosure}>
        <summary className={styles.disclosureSummary}>Show these numbers as a table</summary>
        <table className={styles.table}>
          <caption className={styles.tableCaption}>
            Daily counts and likely-hate rate in the fixture sample
          </caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Relevant</th>
              <th scope="col">Likely hate</th>
              <th scope="col">Rate</th>
            </tr>
          </thead>
          <tbody>
            {DAYS.map((day) => (
              <tr key={day.date}>
                <th scope="row">{day.date}</th>
                <td>{day.relevant}</td>
                <td>{day.likely}</td>
                <td>{ratePercent(day)} percent</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
