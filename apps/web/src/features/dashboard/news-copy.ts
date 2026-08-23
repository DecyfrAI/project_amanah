const DAY_MS = 86_400_000;

export const NEWS_HEADING = 'In the news';

export const NEWS_LEAD =
  'Published reporting that coincides with this window. These articles are context, not Amanah classifications, and they do not explain the figures above or below.';

export function articleLinkLabel(title: string, outlet: string): string {
  return `${title} (opens article on ${outlet})`;
}

export function outboundCue(outlet: string): string {
  return `Opens article on ${outlet}`;
}

export function formatNewsPublishedAt(
  iso: string,
  now: Date = new Date(),
): { absolute: string; relative: string } {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return { absolute: iso, relative: 'date unknown' };
  }

  const absolute = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);

  const days = Math.round((startOfUtcDay(now).getTime() - startOfUtcDay(date).getTime()) / DAY_MS);

  if (days === 0) {
    return { absolute, relative: 'today' };
  }
  if (days === 1) {
    return { absolute, relative: 'yesterday' };
  }
  if (days === -1) {
    return { absolute, relative: 'tomorrow' };
  }
  if (days > 1 && days < 45) {
    return { absolute, relative: `${days} days ago` };
  }
  if (days < -1 && days > -45) {
    return { absolute, relative: `in ${Math.abs(days)} days` };
  }

  return { absolute, relative: absolute };
}

function startOfUtcDay(value: Date): Date {
  return new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), value.getUTCDate()));
}
