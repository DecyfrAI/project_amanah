import { describe, expect, it } from 'vitest';

import {
  dayExplorerHref,
  metricExplorerHref,
  platformDayExplorerHref,
  withExplorerParams,
} from './explorer-href';

describe('explorer drill-down hrefs', () => {
  it('replaces the window and keeps the rest of the selection', () => {
    expect(dayExplorerHref('/app/explorer', '?platform=youtube', '2026-08-15')).toBe(
      '/app/explorer?platform=youtube&from=2026-08-15&to=2026-08-15',
    );
  });

  it('scopes a volume segment to that source and that day', () => {
    expect(
      platformDayExplorerHref('/app/explorer', '?hate_type=threat', 'reddit', '2026-08-16'),
    ).toBe('/app/explorer?hate_type=threat&from=2026-08-16&to=2026-08-16&platform=reddit');
  });

  it('maps review and severity figures onto Explorer filters', () => {
    expect(metricExplorerHref('/app/explorer', '', 'reviewed')).toBe(
      '/app/explorer?review_state=confirmed',
    );
    expect(metricExplorerHref('/app/explorer', '', 'pending')).toBe(
      '/app/explorer?review_state=pending',
    );
    expect(metricExplorerHref('/app/explorer', '?from=2026-08-01&to=2026-08-16', 'severe')).toBe(
      '/app/explorer?from=2026-08-01&to=2026-08-16&severity=2&severity=3',
    );
    expect(metricExplorerHref('/app/explorer', '?platform=youtube', 'rate')).toBe(
      '/app/explorer?platform=youtube',
    );
  });

  it('replaces a repeated filter instead of appending a second copy', () => {
    expect(withExplorerParams('/app/explorer?platform=youtube', { platform: 'reddit' })).toBe(
      '/app/explorer?platform=reddit',
    );
  });
});
