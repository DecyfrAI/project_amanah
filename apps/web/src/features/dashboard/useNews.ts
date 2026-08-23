import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, queryKeys, type NewsList } from '@/api';

import { useDashboardFilters } from './useDashboardFilters';

/**
 * Published news for the same date window as the Overview figures.
 *
 * The list is window-scoped so headlines can coincide with the charts. Platform,
 * hate-type, severity, and review filters are not part of the query key: news is
 * context, not a classified item. See spec.md §3.3 (no causal overclaim) and
 * GET /v1/news. A dedicated `/news` route MAY come later; P0 integrates this
 * stream into the dashboard (spec.md §7.1).
 */
export function useNews(): UseQueryResult<NewsList> {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: queryKeys.news({ from: filters.from, to: filters.to }),
    queryFn: () => apiClient.listNews({ from: filters.from, to: filters.to }),
  });
}
