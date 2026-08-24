import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, queryKeys, type WireContributionsPage } from '@/api';

/**
 * The caller's own contribution history (`GET /v1/me/contributions`).
 *
 * Owner-scoped server-side: this returns only what the authenticated caller
 * created, across submissions, disputes, and prepared reports.
 */
export function useContributions(): UseQueryResult<WireContributionsPage> {
  return useQuery({
    queryKey: queryKeys.contributions,
    queryFn: () => apiClient.listContributions(),
  });
}
