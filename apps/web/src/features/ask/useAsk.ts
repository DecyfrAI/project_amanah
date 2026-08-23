import { useMutation } from '@tanstack/react-query';

import { apiClient, type AssistantAskInput, type AssistantReply } from '@/api';

/**
 * Sends a question about the current window.
 *
 * Creating is an authenticated action. The public dashboard never mounts this.
 */
export function useAsk() {
  return useMutation({
    mutationFn: (input: AssistantAskInput): Promise<AssistantReply> =>
      apiClient.askAssistant(input),
  });
}
