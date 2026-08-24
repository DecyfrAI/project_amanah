import { useMutation } from '@tanstack/react-query';

import { apiClient, type EvidenceClassifyRequest, type ImageClassification } from '@/api';

/** Classify a reviewed catalogue example or a privately stored user upload. */
export function useClassifyEvidence() {
  return useMutation({
    mutationFn: (input: EvidenceClassifyRequest): Promise<ImageClassification> =>
      apiClient.classifyEvidence(input),
  });
}
