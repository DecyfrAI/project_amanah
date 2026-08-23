import { useQuery } from '@tanstack/react-query';

import { apiClient, queryKeys } from '@/api';

export function useInsight(insightId: string) {
  return useQuery({
    queryKey: queryKeys.insight(insightId),
    queryFn: () => apiClient.getInsight(insightId),
  });
}
