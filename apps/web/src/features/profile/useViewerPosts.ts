import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { apiClient, queryKeys, type ViewerPostList } from '@/api';

/**
 * Notes the signed-in viewer has left on insights.
 *
 * Profile reads this rather than walking every thread, so a later live
 * implementation can return only the caller's posts without the page knowing.
 */
export function useViewerPosts(): UseQueryResult<ViewerPostList> {
  return useQuery({
    queryKey: queryKeys.viewerPosts,
    queryFn: () => apiClient.listViewerPosts(),
  });
}
