import { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';

import type { BreakdownRow, OverviewBreakdown } from '@/api';

import { bubbleDiameter, donutSlices } from './breakdown-geometry';
import { chartTone } from './chartTones';
import { formatRate } from './rate';

import styles from './BreakdownChart.module.css';

export interface BreakdownVisualProps {
  breakdown: OverviewBreakdown;
  buildHref: ((dimension: OverviewBreakdown['dimension'], key: string) => string) | null;
  onReportRow?: ((key: string) => void) | undefined;
}

interface RowMarkProps {
  row: BreakdownRow;
  index: number;
  total: number;
  href: string | null;
  onReportRow?: ((key: string) => void) | undefined;
}

function RowName({ href, label }: { href: string | null; label: string }) {
  if (href === null) {
    return <span className={styles.label}>{label}</span>;
  }

  return (
    <Link className={styles.link} to={href}>
      {label}
    </Link>
  );
}

function ReportButton({
  label,
  rowKey,
  onReportRow,
}: {
  label: string;
  rowKey: string;
  onReportRow?: ((key: string) => void) | undefined;
}) {
  const handleClick = useCallback((): void => {
    onReportRow?.(rowKey);
  }, [onReportRow, rowKey]);

  if (onReportRow === undefined) {
    return null;
  }

  return (
    <button type="button" className={styles.report} onClick={handleClick}>
      Start insight on {label}
    </button>
  );
}

function shareOf(count: number, total: number): number {
  return total === 0 ? 0 : count / total;
}

function Counts({ count, total }: { count: number; total: number }) {
  return (
    <span className={styles.figures}>
      {count.toLocaleString('en-GB')} of {total.toLocaleString('en-GB')}
      <span className={styles.share}>{formatRate(shareOf(count, total))}</span>
    </span>
  );
}

function markName(row: BreakdownRow, total: number): string {
  return `${row.label}, ${row.count.toLocaleString('en-GB')} of ${total.toLocaleString('en-GB')}, ${formatRate(shareOf(row.count, total))}`;
}

function hrefFor(
  breakdown: OverviewBreakdown,
  key: string,
  buildHref: BreakdownVisualProps['buildHref'],
): string | null {
  return buildHref === null ? null : buildHref(breakdown.dimension, key);
}

/**
 * Ranked stems. Five similar slices are unreadable as a pie, so type of harm
 * stays linear, with a coloured mark at the value.
 */
export function LollipopVisual({ breakdown, buildHref, onReportRow }: BreakdownVisualProps) {
  const largest = Math.max(1, ...breakdown.rows.map((row) => row.count));

  return (
    <ul className={styles.rows}>
      {breakdown.rows.map((row, index) => {
        const href = hrefFor(breakdown, row.key, buildHref);
        const percent = Math.round((row.count / largest) * 100);
        return (
          <li className={styles.lollipop} key={row.key}>
            <RowName href={href} label={row.label} />
            {href === null ? (
              <span className={styles.stemTrack} aria-hidden="true">
                <WidthMark className={styles.stem} tone={chartTone(index)} percent={percent} />
                <OffsetMark className={styles.dot} tone={chartTone(index)} percent={percent} />
              </span>
            ) : (
              <Link
                className={styles.stemLink}
                to={href}
                aria-label={`Open Explorer for ${markName(row, breakdown.total)}`}
              >
                <span className={styles.stemTrack}>
                  <WidthMark className={styles.stem} tone={chartTone(index)} percent={percent} />
                  <OffsetMark className={styles.dot} tone={chartTone(index)} percent={percent} />
                </span>
              </Link>
            )}
            <Counts count={row.count} total={breakdown.total} />
            <ReportButton label={row.label} rowKey={row.key} onReportRow={onReportRow} />
          </li>
        );
      })}
    </ul>
  );
}

const DONUT_RADIUS = 42;
const DONUT_CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;

/**
 * Two or three parts can be read as a ring if every slice is also named beside
 * it. Used for source platform.
 */
export function DonutVisual({ breakdown, buildHref, onReportRow }: BreakdownVisualProps) {
  const slices = useMemo(
    () => donutSlices(breakdown.rows, breakdown.total, DONUT_CIRCUMFERENCE),
    [breakdown.rows, breakdown.total],
  );

  return (
    <div className={styles.donutLayout}>
      <svg className={styles.donut} viewBox="0 0 120 120" aria-hidden="true">
        <circle className={styles.donutTrack} cx="60" cy="60" r={DONUT_RADIUS} />
        {slices.map((slice, index) => (
          <circle
            key={slice.key}
            className={styles.donutMark}
            data-tone={chartTone(index)}
            cx="60"
            cy="60"
            r={DONUT_RADIUS}
            strokeDasharray={`${String(slice.length)} ${String(DONUT_CIRCUMFERENCE - slice.length)}`}
            strokeDashoffset={String(-slice.offset)}
          />
        ))}
      </svg>
      <ul className={styles.legend}>
        {breakdown.rows.map((row, index) => (
          <LegendRow
            key={row.key}
            row={row}
            index={index}
            total={breakdown.total}
            href={hrefFor(breakdown, row.key, buildHref)}
            onReportRow={onReportRow}
          />
        ))}
      </ul>
    </div>
  );
}

function LegendRow({ row, index, total, href, onReportRow }: RowMarkProps) {
  return (
    <li className={styles.legendRow}>
      {href === null ? (
        <span className={styles.swatch} data-tone={chartTone(index)} aria-hidden="true" />
      ) : (
        <Link
          className={styles.swatchLink}
          to={href}
          aria-label={`Open Explorer for ${markName(row, total)}`}
        >
          <span className={styles.swatch} data-tone={chartTone(index)} aria-hidden="true" />
        </Link>
      )}
      <RowName href={href} label={row.label} />
      <Counts count={row.count} total={total} />
      <ReportButton label={row.label} rowKey={row.key} onReportRow={onReportRow} />
    </li>
  );
}

const BUBBLE_MIN = 44;
const BUBBLE_MAX = 112;

/**
 * Severity as discs. Area follows the count, so a small severe band stays
 * visibly small rather than looking like an equal slice of a pie.
 */
export function BubbleVisual({ breakdown, buildHref, onReportRow }: BreakdownVisualProps) {
  const largest = Math.max(1, ...breakdown.rows.map((row) => row.count));

  return (
    <ul className={styles.bubbles}>
      {breakdown.rows.map((row, index) => {
        const size = bubbleDiameter(row.count, largest, BUBBLE_MIN, BUBBLE_MAX);
        const href = hrefFor(breakdown, row.key, buildHref);
        return (
          <li className={styles.bubbleItem} key={row.key}>
            {href === null ? (
              <BubbleMark tone={chartTone(index)} size={size} />
            ) : (
              <Link
                className={styles.bubbleLink}
                to={href}
                aria-label={`Open Explorer for ${markName(row, breakdown.total)}`}
              >
                <BubbleMark tone={chartTone(index)} size={size} />
              </Link>
            )}
            <RowName href={href} label={row.label} />
            <Counts count={row.count} total={breakdown.total} />
            <ReportButton label={row.label} rowKey={row.key} onReportRow={onReportRow} />
          </li>
        );
      })}
    </ul>
  );
}

/** Coloured bars, used when the other marks would overclaim a simple share. */
export function BarVisual({ breakdown, buildHref, onReportRow }: BreakdownVisualProps) {
  const largest = Math.max(1, ...breakdown.rows.map((row) => row.count));

  return (
    <ul className={styles.rows}>
      {breakdown.rows.map((row, index) => {
        const href = hrefFor(breakdown, row.key, buildHref);
        const percent = Math.round((row.count / largest) * 100);
        return (
          <li className={styles.row} key={row.key}>
            <RowName href={href} label={row.label} />
            {href === null ? (
              <span className={styles.track} aria-hidden="true">
                <WidthMark className={styles.fill} tone={chartTone(index)} percent={percent} />
              </span>
            ) : (
              <Link
                className={styles.barLink}
                to={href}
                aria-label={`Open Explorer for ${markName(row, breakdown.total)}`}
              >
                <span className={styles.track}>
                  <WidthMark className={styles.fill} tone={chartTone(index)} percent={percent} />
                </span>
              </Link>
            )}
            <Counts count={row.count} total={breakdown.total} />
            <ReportButton label={row.label} rowKey={row.key} onReportRow={onReportRow} />
          </li>
        );
      })}
    </ul>
  );
}

function WidthMark({
  className,
  tone,
  percent,
}: {
  className: string | undefined;
  tone: 1 | 2 | 3 | 4 | 5;
  percent: number;
}) {
  const style = useMemo(() => ({ inlineSize: `${String(percent)}%` }), [percent]);

  return <span className={className} data-tone={tone} style={style} />;
}

function OffsetMark({
  className,
  tone,
  percent,
}: {
  className: string | undefined;
  tone: 1 | 2 | 3 | 4 | 5;
  percent: number;
}) {
  const style = useMemo(() => ({ insetInlineStart: `${String(percent)}%` }), [percent]);

  return <span className={className} data-tone={tone} style={style} />;
}

function BubbleMark({ tone, size }: { tone: 1 | 2 | 3 | 4 | 5; size: number }) {
  const style = useMemo(
    () => ({ width: `${String(size)}px`, height: `${String(size)}px` }),
    [size],
  );

  return <span className={styles.bubble} data-tone={tone} style={style} aria-hidden="true" />;
}
