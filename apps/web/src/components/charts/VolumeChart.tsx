import { useCallback, type KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import type { OverviewDay } from '@/api';

import { InfoTip } from '@/components/ui/InfoTip';

import { platformDayExplorerHref } from '@/features/dashboard/explorer-href';

import { chartTone } from './chartTones';
import { formatDay } from './rate';
import { orderedSources, sourceLikelyHate } from './source-stack';

import styles from './VolumeChart.module.css';

interface VolumeChartProps {
  days: readonly OverviewDay[];
  explorerPath?: string | null;
  explorerSearch?: string;
}

const VIEW_WIDTH = 640;
const VIEW_HEIGHT = 220;
const PADDING_X = 44;
const PADDING_Y = 20;

function platformExplorerHref(
  explorerPath: string,
  explorerSearch: string,
  platform: string,
): string {
  const params = new URLSearchParams(
    explorerSearch.startsWith('?') ? explorerSearch.slice(1) : explorerSearch,
  );
  params.set('platform', platform);
  return `${explorerPath}?${params.toString()}`;
}

/**
 * Daily likely-hate volume, stacked by source.
 *
 * Sources keep one order across the window (largest total at the bottom), so a
 * day never reshuffles the legend. An uncollected day draws a stub at the axis,
 * never a zero-height stack, which would read as "we looked and found none".
 */
export function VolumeChart({ days, explorerPath = null, explorerSearch = '' }: VolumeChartProps) {
  const navigate = useNavigate();
  const sources = orderedSources(days);
  const maxHate = Math.max(1, ...days.map((day) => (day.collected ? (day.likelyHate ?? 0) : 0)));
  const step = (VIEW_WIDTH - PADDING_X * 2) / Math.max(1, days.length);
  const barWidth = Math.max(2, step * 0.62);
  const scale = (value: number): number => ((VIEW_HEIGHT - PADDING_Y * 2) * value) / maxHate;

  const collected = days.filter((day) => day.collected);
  const totalHate = collected.reduce((sum, day) => sum + (day.likelyHate ?? 0), 0);
  const gaps = days.filter((day) => !day.collected);

  const openSource = useCallback(
    (platform: string, date: string): void => {
      if (explorerPath === null) {
        return;
      }
      void navigate(platformDayExplorerHref(explorerPath, explorerSearch, platform, date));
    },
    [explorerPath, explorerSearch, navigate],
  );

  return (
    <figure className={styles.figure}>
      <div className={styles.captionRow}>
        <figcaption className={styles.caption}>
          Likely-hate items collected each day, stacked by source. Larger sources sit at the bottom
          of every bar so the legend stays stable across the window.
        </figcaption>
        <InfoTip label="Stacked volume" placement="card">
          Daily likely-hate volume stacked by source. An uncollected day draws a stub at the axis,
          never a zero-height stack.
        </InfoTip>
      </div>

      <p className={styles.summary}>
        {totalHate.toLocaleString('en-GB')} items classified as likely anti-Muslim hate across{' '}
        {collected.length.toLocaleString('en-GB')} collected days.
        {sources.length > 0 &&
          ` Stacked largest to smallest: ${sources.map((source) => source.label).join(', ')}.`}
        {gaps.length > 0 &&
          ` ${gaps.map((day) => formatDay(day.date)).join(' and ')} ${gaps.length === 1 ? 'has' : 'have'} no bar because collection failed, which is not the same as a day with none.`}
      </p>

      <svg
        className={styles.chart}
        viewBox={`0 0 ${String(VIEW_WIDTH)} ${String(VIEW_HEIGHT)}`}
        aria-hidden={explorerPath === null ? true : undefined}
        role={explorerPath === null ? undefined : 'img'}
        aria-label={
          explorerPath === null
            ? undefined
            : 'Daily likely-hate volume by source. Use the legend links to open each source in Explorer.'
        }
      >
        <line
          className={styles.axis}
          x1={PADDING_X}
          y1={VIEW_HEIGHT - PADDING_Y}
          x2={VIEW_WIDTH - PADDING_X}
          y2={VIEW_HEIGHT - PADDING_Y}
        />
        {days.map((day, index) => {
          const x = PADDING_X + step * index + (step - barWidth) / 2;
          if (!day.collected) {
            return (
              <rect
                key={day.date}
                className={styles.gap}
                x={x}
                y={VIEW_HEIGHT - PADDING_Y - 6}
                width={barWidth}
                height={6}
                fill="var(--color-chart-gap)"
              />
            );
          }

          let cursor = VIEW_HEIGHT - PADDING_Y;
          return (
            <g key={day.date}>
              {sources.map((source, sourceIndex) => {
                const count = sourceLikelyHate(day, source.key);
                if (count === 0) {
                  return null;
                }
                const height = scale(count);
                cursor -= height;
                return (
                  <SourceBarSegment
                    key={source.key}
                    sourceKey={source.key}
                    label={source.label}
                    date={day.date}
                    dateLabel={formatDay(day.date)}
                    tone={chartTone(sourceIndex)}
                    x={x}
                    y={cursor}
                    width={barWidth}
                    height={height}
                    interactive={explorerPath !== null}
                    onOpen={openSource}
                  />
                );
              })}
            </g>
          );
        })}
      </svg>

      <p className={styles.legend}>
        {sources.map((source, index) => (
          <span key={source.key} className={styles.legendItem}>
            <span className={styles.keySource} data-tone={chartTone(index)} aria-hidden="true" />
            {explorerPath === null ? (
              source.label
            ) : (
              <Link
                className={styles.legendLink}
                to={platformExplorerHref(explorerPath, explorerSearch, source.key)}
              >
                {source.label}
              </Link>
            )}
          </span>
        ))}
        <span className={styles.legendItem}>
          <span className={styles.keyGap} aria-hidden="true" /> No collection
        </span>
      </p>

      <details className={styles.disclosure}>
        <summary className={styles.disclosureSummary}>Show these volumes as a table</summary>
        <SourceVolumeTable days={days} sources={sources} />
      </details>
    </figure>
  );
}

function SourceBarSegment({
  sourceKey,
  label,
  date,
  dateLabel,
  tone,
  x,
  y,
  width,
  height,
  interactive,
  onOpen,
}: {
  sourceKey: string;
  label: string;
  date: string;
  dateLabel: string;
  tone: 1 | 2 | 3 | 4 | 5;
  x: number;
  y: number;
  width: number;
  height: number;
  interactive: boolean;
  onOpen: (platform: string, date: string) => void;
}) {
  const handleClick = useCallback((): void => {
    onOpen(sourceKey, date);
  }, [date, onOpen, sourceKey]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<SVGRectElement>): void => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        onOpen(sourceKey, date);
      }
    },
    [date, onOpen, sourceKey],
  );

  if (!interactive) {
    return (
      <rect
        className={styles.sourceBar}
        data-tone={tone}
        x={x}
        y={y}
        width={width}
        height={height}
        fill={`var(--color-chart-cat-${String(tone)})`}
      />
    );
  }

  return (
    <rect
      className={styles.sourceBarInteractive}
      data-tone={tone}
      x={x}
      y={y}
      width={width}
      height={height}
      fill={`var(--color-chart-cat-${String(tone)})`}
      tabIndex={0}
      aria-label={`Open Explorer for ${label} on ${dateLabel}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
    />
  );
}

function SourceVolumeTable({
  days,
  sources,
}: {
  days: readonly OverviewDay[];
  sources: ReturnType<typeof orderedSources>;
}) {
  return (
    <table className={styles.table}>
      <caption className={styles.tableCaption}>
        Daily likely-hate counts by source, with the day total
      </caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          {sources.map((source) => (
            <th key={source.key} scope="col">
              {source.label}
            </th>
          ))}
          <th scope="col">Total likely hate</th>
        </tr>
      </thead>
      <tbody>
        {days.map((day) => (
          <tr key={day.date}>
            <th scope="row">{formatDay(day.date)}</th>
            {day.collected ? (
              <>
                {sources.map((source) => (
                  <td key={source.key}>{sourceLikelyHate(day, source.key)}</td>
                ))}
                <td>{day.likelyHate}</td>
              </>
            ) : (
              <td className={styles.gapCell} colSpan={sources.length + 1}>
                No collection on this day
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
