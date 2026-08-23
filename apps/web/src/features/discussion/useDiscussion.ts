import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient, queryKeys } from '@/api';
import type { CreatePostInput, ReactionKind } from '@/api/contracts';

export function useDiscussion(insightId: string) {
  const queryClient = useQueryClient();
  const discussionQuery = useQuery({
    queryKey: queryKeys.discussion(insightId),
    queryFn: () => apiClient.getDiscussion(insightId),
  });

  const invalidate = (): void => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.discussion(insightId) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.viewerPosts });
  };

  const createPost = useMutation({
    mutationFn: (input: CreatePostInput) => apiClient.createPost(insightId, input),
    onSuccess: invalidate,
  });

  const react = useMutation({
    mutationFn: ({ postId, kind }: { postId: string; kind: ReactionKind }) =>
      apiClient.reactToPost(postId, kind),
    onSuccess: invalidate,
  });

  const retract = useMutation({
    mutationFn: (postId: string) => apiClient.retractPost(postId),
    onSuccess: invalidate,
  });

  return { discussionQuery, createPost, react, retract };
}
