import type { OverviewDay } from '@/api/contracts';

/**
 * The daily likely-hate rate, or null when there is nothing to divide.
 *
 * Null means "we cannot state a rate for this day", which covers both a failed
 * collection and a day with no relevant items. Neither is zero, and returning 0
 * for either would put a point on the axis that reads as a calm day.
 */
export function dailyRate(day: OverviewDay): number | null {
  if (!day.collected || day.relevant === null || day.likelyHate === null || day.relevant === 0) {
    return null;
  }
  return day.likelyHate / day.relevant;
}

export function formatRate(rate: number | null): string {
  if (rate === null) {
    return 'No rate';
  }
  return `${(rate * 100).toFixed(1)}%`;
}

/** "1 August", from an ISO date, without pulling in a date library. */
export function formatDay(date: string): string {
  const parsed = new Date(`${date}T00:00:00Z`);
  return parsed.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  });
}

export function dayOfMonth(date: string): string {
  return String(Number(date.slice(8, 10)));
}
