import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, type ExplorerItem } from '@/api';

export function useImagePosts(): UseQueryResult<readonly ExplorerItem[]> {
  return useQuery({
    queryKey: ['image-posts'],
    queryFn: async () => {
      const page = await apiClient.searchItems({});
      return page.items.filter((item) => item.image !== undefined && item.image !== null);
    },
  });
}
