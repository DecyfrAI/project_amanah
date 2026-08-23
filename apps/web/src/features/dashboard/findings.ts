import type { CreateInsightInput, OverviewBreakdown, OverviewDay, OverviewMetric } from '@/api';
import { formatDay, formatRate } from '@/components/charts/rate';
import { dailyRate } from '@/components/charts/rate';

/**
 * Turns a collected day into a snapshot the Insights tab can hold.
 *
 * The claim is the same sentence the chart already reads out, so the insight
 * cannot say more than the figure did. An uncollected day is refused: there is
 * no finding to freeze.
 */
export function findingFromDay(
  day: OverviewDay,
  explorerHref: string,
  sources: readonly string[],
): CreateInsightInput | null {
  if (!day.collected || day.relevant === null || day.likelyHate === null) {
    return null;
  }

  const rate = dailyRate(day);
  const dayLabel = formatDay(day.date);

  return {
    title: `Likely-hate rate on ${dayLabel}`,
    claim: `${dayLabel}: ${String(day.likelyHate)} of ${String(day.relevant)} Muslim-related items classified as likely hate, ${formatRate(rate)}.`,
    numerator: day.likelyHate,
    denominator: day.relevant,
    metric: 'likely_hate_rate',
    from: day.date,
    to: day.date,
    explorerHref,
    figureLabel: `Daily likely-hate rate, ${day.date}`,
    sources: [...sources],
    itemsObserved: day.observed ?? day.relevant,
    itemsRelevant: day.relevant,
  };
}

/**
 * Turns one breakdown row into a snapshot.
 *
 * The share of the total travels in the claim. The rate against the row's own
 * denominator travels as the fact, so a later reader can see both.
 */
export function findingFromBreakdownRow(
  breakdown: OverviewBreakdown,
  key: string,
  from: string,
  to: string,
  explorerHref: string,
  sources: readonly string[],
  itemsObserved: number,
  itemsRelevant: number,
): CreateInsightInput | null {
  const row = breakdown.rows.find((entry) => entry.key === key);
  if (row === undefined) {
    return null;
  }

  const share = breakdown.total === 0 ? 0 : row.count / breakdown.total;

  return {
    title: `${row.label} in the current window`,
    claim: `${row.label}: ${row.count.toLocaleString('en-GB')} of ${breakdown.total.toLocaleString('en-GB')} ${breakdown.countLabel} (${formatRate(share)}). Rate against ${breakdown.denominatorLabel}: ${formatRate(row.rate)}.`,
    numerator: row.count,
    denominator: row.denominator,
    metric: breakdown.dimension,
    from,
    to,
    explorerHref,
    figureLabel: `${breakdown.label}, ${row.label}`,
    sources: [...sources],
    itemsObserved,
    itemsRelevant,
  };
}

/**
 * Turns a key figure into a snapshot when the pair is already on the card.
 *
 * A count or rate without both parts is refused: there is no finding to freeze
 * that a later reader could check.
 */
export function findingFromMetric(
  metric: OverviewMetric,
  from: string,
  to: string,
  explorerHref: string,
  sources: readonly string[],
  itemsObserved: number,
  itemsRelevant: number,
): CreateInsightInput | null {
  if (
    metric.insufficientVolume ||
    metric.value === null ||
    metric.numerator === null ||
    metric.denominator === null
  ) {
    return null;
  }

  const valueText =
    metric.unit === 'rate' ? formatRate(metric.value) : metric.value.toLocaleString('en-GB');

  return {
    title: metric.label,
    claim: `${metric.label}: ${valueText} (${metric.numerator.toLocaleString('en-GB')} of ${metric.denominator.toLocaleString('en-GB')}). ${metric.definition}`,
    numerator: metric.numerator,
    denominator: metric.denominator,
    metric: metric.id,
    from,
    to,
    explorerHref,
    figureLabel: metric.label,
    sources: [...sources],
    itemsObserved,
    itemsRelevant,
  };
}
