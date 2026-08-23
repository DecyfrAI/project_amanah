/**
 * Builds Explorer URLs from a dashboard figure.
 *
 * A click on a point, bar, or card has to land on the same filters the figure
 * described. Extra keys replace the same names and leave the rest of the
 * window intact.
 */

export function withExplorerParams(
  href: string,
  extras: Record<string, string | readonly string[]>,
): string {
  const queryAt = href.indexOf('?');
  const path = queryAt === -1 ? href : href.slice(0, queryAt);
  const search = queryAt === -1 ? '' : href.slice(queryAt + 1);
  const params = new URLSearchParams(search);

  for (const [key, value] of Object.entries(extras)) {
    params.delete(key);
    if (typeof value === 'string') {
      params.set(key, value);
      continue;
    }
    for (const item of value) {
      params.append(key, item);
    }
  }

  const query = params.toString();
  return query === '' ? path : `${path}?${query}`;
}

export function explorerBaseHref(path: string, search: string): string {
  if (search === '' || search.startsWith('?')) {
    return `${path}${search}`;
  }
  return `${path}?${search}`;
}

export function dayExplorerHref(path: string, search: string, date: string): string {
  return withExplorerParams(explorerBaseHref(path, search), { from: date, to: date });
}

export function platformDayExplorerHref(
  path: string,
  search: string,
  platform: string,
  date: string,
): string {
  return withExplorerParams(dayExplorerHref(path, search, date), { platform });
}

export function metricExplorerHref(path: string, search: string, metricId: string): string {
  const base = explorerBaseHref(path, search);
  if (metricId === 'reviewed') {
    return withExplorerParams(base, { review_state: 'confirmed' });
  }
  if (metricId === 'pending') {
    return withExplorerParams(base, { review_state: 'pending' });
  }
  if (metricId === 'severe') {
    return withExplorerParams(base, { severity: ['2', '3'] });
  }
  return base;
}
