import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, queryKeys, type FilterOptions, type Overview } from '@/api';
import { useDashboardFilters } from './useDashboardFilters';

/**
 * The dashboard's figures for the filters currently in the URL.
 *
 * The URL is the source of truth for scope, so a view can be shared and read the
 * same way by the person who receives it. Every filter is part of the query key,
 * so the cache cannot serve a reading from a window nobody asked for.
 */
export function useOverview(): UseQueryResult<Overview> {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: queryKeys.overview(filters),
    queryFn: () => apiClient.getOverview(filters),
  });
}

/**
 * The filter values the service will accept.
 *
 * Kept separate from the figures because the option list changes far less often
 * than a window does, and because the calendar has to know the available range
 * before it can refuse a date that has no collection behind it.
 */
export function useFilterOptions(): UseQueryResult<FilterOptions> {
  return useQuery({
    queryKey: queryKeys.filterOptions,
    queryFn: () => apiClient.getFilterOptions(),
    staleTime: Infinity,
  });
}
