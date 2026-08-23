import { useMutation } from '@tanstack/react-query';

import { apiClient, type EvidenceClassifyRequest, type ImageClassification } from '@/api';

/**
 * Fixture image check for F-S14. Filename and size only. Pixels stay in the tab.
 */
export function useClassifyEvidence() {
  return useMutation({
    mutationFn: (input: EvidenceClassifyRequest): Promise<ImageClassification> =>
      apiClient.classifyEvidence(input),
  });
}
