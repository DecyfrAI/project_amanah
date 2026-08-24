import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { apiClient, queryKeys, type CreateInsightInput, type Insight } from '@/api';

/**
 * Starts a snapshot insight from a figure and opens its thread.
 *
 * Creating is an authenticated action. The public dashboard never calls this.
 */
export function useCreateInsight() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (input: CreateInsightInput) => apiClient.createInsight(input),
    onSuccess: (insight: Insight): void => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.insights });
      // `created: true` lets the detail page show its "added to Insights"
      // confirmation (PA-04) without treating every later visit as a creation.
      void navigate(`/app/insights/${insight.id}`, { state: { created: true } });
    },
  });
}
