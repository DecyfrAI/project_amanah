import { useQuery } from '@tanstack/react-query';

import { apiClient, queryKeys } from '@/api';

export function useImageExamples() {
  return useQuery({
    queryKey: queryKeys.imageExamples,
    queryFn: () => apiClient.listImageExamples(),
  });
}
