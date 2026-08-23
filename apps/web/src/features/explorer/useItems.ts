import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, queryKeys, type ExplorerPage } from '@/api';
import { useDashboardFilters } from '@/features/dashboard/useDashboardFilters';

/**
 * Item-level results for the filters in the URL.
 *
 * The Explorer and the dashboard read the same filter state, which is what makes
 * a drill-down land on the same scope the figure described.
 */
export function useItems(): UseQueryResult<ExplorerPage> {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: queryKeys.items(filters),
    queryFn: () => apiClient.searchItems(filters),
  });
}
