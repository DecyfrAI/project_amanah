import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import type { OverviewDay } from '@/api/contracts';

import { InfoTip } from '@/components/ui/InfoTip';

import { dayExplorerHref } from '@/features/dashboard/explorer-href';

import { DailySeriesTable } from './DailySeriesTable';
import { dailyRate, dayOfMonth, formatDay, formatRate } from './rate';

import styles from './DailyRateChart.module.css';

interface DailyRateChartProps {
  days: readonly OverviewDay[];
  /**
   * Route holding the supporting records, or `null` where they are out of reach.
   * Records sit behind authentication, so the public dashboard passes `null`
   * rather than offering a link that lands on a login form.
   */
  explorerPath?: string | null;
  /**
   * Current dashboard filters as a query string. The day link replaces the date
   * range and keeps every other selection, so the Explorer opens on the same
   * slice the figure described.
   */
  explorerSearch?: string;
  /**
   * Starts a snapshot insight on the selected collected day. Absent on the
   * public dashboard, where creating a thread is an authenticated action.
   */
  onReportDay?: ((day: OverviewDay) => void) | undefined;
}

const VIEW_WIDTH = 640;
const VIEW_HEIGHT = 220;
const PADDING_X = 44;
const PADDING_Y = 24;
const AXIS_STEPS = [0, 0.1, 0.2, 0.3, 0.4] as const;
const AXIS_MAX = 0.4;

interface Point {
  readonly day: OverviewDay;
  readonly rate: number | null;
  readonly x: number;
  readonly y: number | null;
}

function buildPoints(days: readonly OverviewDay[]): readonly Point[] {
  const span = Math.max(1, days.length - 1);
  const plotWidth = VIEW_WIDTH - PADDING_X - PADDING_Y;
  const plotHeight = VIEW_HEIGHT - PADDING_Y * 2;

  return days.map((day, index) => {
    const rate = dailyRate(day);
    return {
      day,
      rate,
      x: PADDING_X + (index / span) * plotWidth,
      y: rate === null ? null : PADDING_Y + plotHeight * (1 - Math.min(rate, AXIS_MAX) / AXIS_MAX),
    };
  });
}

/**
 * Consecutive runs of collected days.
 *
 * The line is drawn as one polyline per run rather than one across the whole
 * window, which is what makes a failed collection day render as a break. Joining
 * across it would invent a reading for a day we never saw.
 */
function buildSegments(points: readonly Point[]): readonly string[] {
  const segments: string[] = [];
  let current: string[] = [];

  for (const point of points) {
    if (point.y === null) {
      if (current.length > 1) {
        segments.push(current.join(' '));
      }
      current = [];
      continue;
    }
    current.push(`${point.x},${point.y}`);
  }

  if (current.length > 1) {
    segments.push(current.join(' '));
  }

  return segments;
}

interface DayButtonProps {
  day: OverviewDay;
  isSelected: boolean;
  onSelect: (date: string) => void;
}

/**
 * One keyboard-reachable data point.
 *
 * Every day is a button, including an uncollected one, so a reader using the
 * keyboard reaches the gap as well as the readings. Its accessible name states
 * the date and either the rate or that nothing was collected.
 */
interface ReportDayButtonProps {
  day: OverviewDay;
  onReport: (day: OverviewDay) => void;
}

function ReportDayButton({ day, onReport }: ReportDayButtonProps) {
  const handleClick = useCallback((): void => {
    onReport(day);
  }, [day, onReport]);

  return (
    <button type="button" className={styles.report} onClick={handleClick}>
      Start an insight on {formatDay(day.date)}
    </button>
  );
}

function DayButton({ day, isSelected, onSelect }: DayButtonProps) {
  const handleClick = useCallback((): void => {
    onSelect(day.date);
  }, [day.date, onSelect]);

  return (
    <button
      type="button"
      className={day.collected ? styles.dayButton : styles.dayButtonGap}
      aria-pressed={isSelected}
      onClick={handleClick}
    >
      <span aria-hidden="true">{dayOfMonth(day.date)}</span>
      <span className="visually-hidden">
        {formatDay(day.date)}
        {day.collected ? `, ${formatRate(dailyRate(day))}` : ', no collection'}
      </span>
    </button>
  );
}

function PlotPoint({
  date,
  x,
  y,
  href,
}: {
  date: string;
  x: number;
  y: number;
  href: string | null;
}) {
  const mark = <circle className={styles.pointButton} cx={x} cy={y} r={6} />;
  if (href === null) {
    return mark;
  }

  return (
    <Link to={href} aria-label={`Open Explorer for ${formatDay(date)}`}>
      {mark}
    </Link>
  );
}

export function DailyRateChart({
  days,
  explorerPath = '/app/explorer',
  explorerSearch = '',
  onReportDay,
}: DailyRateChartProps) {
  const points = useMemo(() => buildPoints(days), [days]);
  const segments = useMemo(() => buildSegments(points), [points]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const handleSelect = useCallback((date: string): void => {
    setSelectedDate((current) => (current === date ? null : date));
  }, []);

  const selected = points.find((point) => point.day.date === selectedDate) ?? null;
  const collectedDays = days.filter((day) => day.collected);
  const gapDays = days.filter((day) => !day.collected);
  const plotBottom = VIEW_HEIGHT - PADDING_Y;

  return (
    <figure className={styles.figure}>
      <figcaption className={styles.caption}>
        <div className={styles.titleRow}>
          <h3 className={styles.title}>Daily likely anti-Muslim hate rate</h3>
          <InfoTip label="Daily likely anti-Muslim hate rate" placement="card">
            Likely anti-Muslim items as a share of Muslim-related items, by day. A missing
            collection day is a break in the line, never a zero. These are model classifications,
            not confirmed findings.
          </InfoTip>
        </div>
        <p className={styles.summary}>
          Likely anti-Muslim items as a share of Muslim-related items, by day.{' '}
          {collectedDays.length} of {days.length} days were collected
          {gapDays.length > 0
            ? `, and ${gapDays.map((day) => formatDay(day.date)).join(', ')} ${
                gapDays.length === 1 ? 'is' : 'are'
              } drawn as a break in the line rather than as zero.`
            : '.'}{' '}
          These are model classifications, not confirmed findings.
        </p>
      </figcaption>

      <svg
        className={styles.chart}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        aria-hidden={explorerPath === null ? true : undefined}
        focusable="false"
      >
        {AXIS_STEPS.map((step) => {
          const y = PADDING_Y + (VIEW_HEIGHT - PADDING_Y * 2) * (1 - step / AXIS_MAX);
          return (
            <g key={step}>
              <line
                className={styles.grid}
                x1={PADDING_X}
                x2={VIEW_WIDTH - PADDING_Y}
                y1={y}
                y2={y}
              />
              <text className={styles.axisLabel} x={PADDING_X - 8} y={y + 4} textAnchor="end">
                {`${Math.round(step * 100)}%`}
              </text>
            </g>
          );
        })}

        {points.map((point) =>
          point.y === null ? (
            <line
              key={point.day.date}
              className={styles.gapMark}
              x1={point.x}
              x2={point.x}
              y1={PADDING_Y}
              y2={plotBottom}
            />
          ) : null,
        )}

        {segments.map((segment) => (
          <polyline key={segment} className={styles.line} points={segment} fill="none" />
        ))}

        {points.map((point) =>
          point.y === null ? null : (
            <PlotPoint
              key={point.day.date}
              date={point.day.date}
              x={point.x}
              y={point.y}
              href={
                explorerPath === null
                  ? null
                  : dayExplorerHref(explorerPath, explorerSearch, point.day.date)
              }
            />
          ),
        )}

        {selected?.y != null && (
          <circle className={styles.selectedPoint} cx={selected.x} cy={selected.y} r={6} />
        )}
      </svg>

      <fieldset className={styles.days}>
        <legend className={styles.legend}>Inspect a day in this window</legend>
        {days.map((day) => (
          <DayButton
            key={day.date}
            day={day}
            isSelected={selectedDate === day.date}
            onSelect={handleSelect}
          />
        ))}
      </fieldset>

      <output className={styles.readout} aria-live="polite">
        {selected === null
          ? 'Select a day to read its counts.'
          : selected.day.collected
            ? `${formatDay(selected.day.date)}: ${selected.day.likelyHate} of ${selected.day.relevant} Muslim-related items classified as likely hate, ${formatRate(selected.rate)}.`
            : `${formatDay(selected.day.date)}: collection failed, so no rate can be stated for this day.`}
      </output>

      {selected !== null && selected.day.collected && (
        <div className={styles.actions}>
          {explorerPath !== null && (
            <Link
              className={styles.drillDown}
              to={dayExplorerHref(explorerPath, explorerSearch, selected.day.date)}
            >
              View supporting records for {formatDay(selected.day.date)}
            </Link>
          )}
          {onReportDay !== undefined && (
            <ReportDayButton day={selected.day} onReport={onReportDay} />
          )}
        </div>
      )}

      <details className={styles.disclosure}>
        <summary className={styles.disclosureSummary}>Show these numbers as a table</summary>
        <DailySeriesTable days={days} explorerPath={explorerPath} explorerSearch={explorerSearch} />
      </details>
    </figure>
  );
}
