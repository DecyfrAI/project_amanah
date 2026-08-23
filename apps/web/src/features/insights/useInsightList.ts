import { useQuery } from '@tanstack/react-query';

import { apiClient, queryKeys } from '@/api';

export function useInsightList() {
  return useQuery({
    queryKey: queryKeys.insights,
    queryFn: () => apiClient.listInsights(),
  });
}
