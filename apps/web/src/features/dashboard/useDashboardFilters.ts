import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

import type { OverviewFilters } from '@/api';

/** Query parameter names, shared by the dashboard and the Explorer. */
export const FILTER_PARAMS = {
  from: 'from',
  to: 'to',
  platform: 'platform',
  hateType: 'hate_type',
  severity: 'severity',
  reviewState: 'review_state',
  q: 'q',
} as const;

export interface DashboardFilterControls {
  filters: OverviewFilters;
  /** Replaces the date range, leaving every other filter alone. */
  setRange: (from: string, to: string) => void;
  /** Adds or removes one value of a multi-select filter. */
  toggleValue: (param: string, value: string) => void;
  /** Replaces the Explorer keyword query. */
  setQuery: (query: string) => void;
  clearAll: () => void;
  activeCount: number;
  /** The same filters as a query string, for a link into another view. */
  toSearch: () => string;
}

function readList(params: URLSearchParams, key: string): string[] {
  return params.getAll(key).filter((value) => value !== '');
}

/**
 * Reads and writes the dashboard filters in the URL.
 *
 * Nothing about scope lives in component state: a filter the URL does not carry
 * cannot be shared, bookmarked, or cited in a discussion note, and a screenshot
 * of a figure whose scope nobody can reproduce is exactly the kind of claim this
 * product must not make. Date changes replace history so the back button steps
 * through views rather than through keystrokes.
 */
export function useDashboardFilters(): DashboardFilterControls {
  const [params, setParams] = useSearchParams();

  const filters = useMemo<OverviewFilters>(() => {
    const from = params.get(FILTER_PARAMS.from);
    const to = params.get(FILTER_PARAMS.to);
    const query = params.get(FILTER_PARAMS.q);
    return {
      ...(from === null ? {} : { from }),
      ...(to === null ? {} : { to }),
      ...(query === null || query.trim() === '' ? {} : { q: query }),
      platforms: readList(params, FILTER_PARAMS.platform),
      hateTypes: readList(params, FILTER_PARAMS.hateType),
      severityBands: readList(params, FILTER_PARAMS.severity),
      reviewStates: readList(params, FILTER_PARAMS.reviewState),
    };
  }, [params]);

  const setRange = useCallback(
    (from: string, to: string): void => {
      const next = new URLSearchParams(params);
      next.set(FILTER_PARAMS.from, from);
      next.set(FILTER_PARAMS.to, to);
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  const toggleValue = useCallback(
    (param: string, value: string): void => {
      const next = new URLSearchParams(params);
      const current = next.getAll(param);
      next.delete(param);
      for (const entry of current) {
        if (entry !== value) {
          next.append(param, entry);
        }
      }
      if (!current.includes(value)) {
        next.append(param, value);
      }
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  const setQuery = useCallback(
    (query: string): void => {
      const next = new URLSearchParams(params);
      const trimmed = query.trim();
      if (trimmed === '') {
        next.delete(FILTER_PARAMS.q);
      } else {
        next.set(FILTER_PARAMS.q, trimmed);
      }
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  const clearAll = useCallback((): void => {
    const next = new URLSearchParams(params);
    for (const key of Object.values(FILTER_PARAMS)) {
      next.delete(key);
    }
    setParams(next, { replace: true });
  }, [params, setParams]);

  const activeCount =
    (filters.platforms?.length ?? 0) +
    (filters.hateTypes?.length ?? 0) +
    (filters.severityBands?.length ?? 0) +
    (filters.reviewStates?.length ?? 0) +
    (filters.q !== undefined && filters.q.trim() !== '' ? 1 : 0);

  const toSearch = useCallback((): string => {
    const next = new URLSearchParams();
    for (const key of Object.values(FILTER_PARAMS)) {
      for (const value of params.getAll(key)) {
        next.append(key, value);
      }
    }
    const query = next.toString();
    return query === '' ? '' : `?${query}`;
  }, [params]);

  return { filters, setRange, toggleValue, setQuery, clearAll, activeCount, toSearch };
}
