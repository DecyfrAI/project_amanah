/**
 * Shared geometry for daily bars stacked by source.
 *
 * Sources are ordered by their total likely-hate count across the window, so a
 * day never reshuffles the legend. An uncollected day contributes nothing.
 */

import type { OverviewDay } from '@/api/contracts';

export interface OrderedSource {
  readonly key: string;
  readonly label: string;
  readonly totalLikelyHate: number;
}

export function orderedSources(days: readonly OverviewDay[]): readonly OrderedSource[] {
  const totals = new Map<string, { label: string; totalLikelyHate: number }>();

  for (const day of days) {
    for (const source of day.sources) {
      const current = totals.get(source.key);
      if (current === undefined) {
        totals.set(source.key, { label: source.label, totalLikelyHate: source.likelyHate });
      } else {
        totals.set(source.key, {
          label: current.label,
          totalLikelyHate: current.totalLikelyHate + source.likelyHate,
        });
      }
    }
  }

  return [...totals.entries()]
    .map(([key, value]) => ({
      key,
      label: value.label,
      totalLikelyHate: value.totalLikelyHate,
    }))
    .toSorted((left, right) =>
      right.totalLikelyHate === left.totalLikelyHate
        ? left.key.localeCompare(right.key)
        : right.totalLikelyHate - left.totalLikelyHate,
    );
}

/** Likely-hate count for one source on one day, or zero when that source is absent. */
export function sourceLikelyHate(day: OverviewDay, key: string): number {
  return day.sources.find((source) => source.key === key)?.likelyHate ?? 0;
}
