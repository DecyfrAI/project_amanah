import { useMutation } from '@tanstack/react-query';

import { apiClient, type ReportDraft, type ReportDraftRequest } from '@/api';

/**
 * Prepares platform-report wording. F-S14.
 *
 * This never submits the report. The mutation returns wording for the person
 * to copy or download, then paste into the official form.
 */
export function usePrepareReportDraft() {
  return useMutation({
    mutationFn: (input: ReportDraftRequest): Promise<ReportDraft> =>
      apiClient.prepareReportDraft(input),
  });
}
