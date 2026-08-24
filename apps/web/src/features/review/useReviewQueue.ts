import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';

import {
  apiClient,
  queryKeys,
  type AppendDecisionRequest,
  type ReviewQueuePage,
  type ReviewTaskDetail,
} from '@/api';

export function useReviewQueue(): UseQueryResult<ReviewQueuePage> {
  return useQuery({
    queryKey: queryKeys.reviewTasks,
    queryFn: () => apiClient.listReviewTasks(),
  });
}

/**
 * Take a task under a lease.
 *
 * A failed claim is a real outcome, not an error to retry: another reviewer got
 * there first, and retrying would take the task from under them.
 */
export function useClaimReviewTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => apiClient.claimReviewTask(taskId),
    retry: 0,
    onSuccess: (): void => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.reviewTasks });
    },
  });
}

/**
 * Append one decision.
 *
 * Never retried. A decision is an append: a retry after an ambiguous failure
 * would write a second one, and the queue would show a reviewer deciding twice.
 */
export function useAppendDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      taskId,
      input,
    }: {
      taskId: string;
      input: AppendDecisionRequest;
    }): Promise<ReviewTaskDetail> => apiClient.appendReviewDecision(taskId, input),
    retry: 0,
    onSuccess: (): void => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.reviewTasks });
    },
  });
}
