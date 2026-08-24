import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, queryKeys, type ExplorerItemDetail } from '@/api';

/**
 * One item and its full model disclosure (`GET /v1/items/{id}`).
 *
 * Enabled only for a non-empty id, so a malformed route does not issue a
 * request whose failure the page would have to explain.
 */
export function useItem(itemId: string): UseQueryResult<ExplorerItemDetail> {
  return useQuery({
    queryKey: queryKeys.item(itemId),
    queryFn: () => apiClient.getItem(itemId),
    enabled: itemId !== '',
  });
}
