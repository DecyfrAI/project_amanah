import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  apiClient,
  queryKeys,
  type PrepareReportInput,
  type ReportOutcomeInput,
  type WirePolicyAnalysis,
  type WirePreparedReport,
} from '@/api';

/**
 * Reads the reviewed policy candidates for one item
 * (`POST /v1/items/{id}/policy-analysis`).
 *
 * Every candidate is a *possible* match carrying its score, official link,
 * version, and last-reviewed date, so a person judges the match rather than
 * inheriting it. An item the classifier did not read as anti-Muslim returns no
 * candidates by design.
 */
export function useAnalyzePolicies() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (contentItemId: string) => apiClient.analyzePolicies(contentItemId),
    onSuccess: (analysis: WirePolicyAnalysis): void => {
      queryClient.setQueryData(queryKeys.policyAnalysis(analysis.content_item_id), analysis);
    },
  });
}

/**
 * Saves a prepared report against the policy version the person confirmed
 * (`POST /v1/prepared-reports`).
 *
 * Nothing is transmitted to the platform. The record is the user's own
 * preparation, and the contributions history is invalidated so it appears there.
 */
export function useSavePreparedReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PrepareReportInput) => apiClient.savePreparedReport(input),
    onSuccess: (): void => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.contributions });
    },
  });
}

/**
 * Records what the owner says they did with a prepared report
 * (`PATCH /v1/prepared-reports/{id}`).
 *
 * `submitted` is the user's own account of filing it, never a platform receipt:
 * the product has no channel that receives one.
 */
export function useRecordReportOutcome() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reportId, input }: { reportId: string; input: ReportOutcomeInput }) =>
      apiClient.recordReportOutcome(reportId, input),
    onSuccess: (_report: WirePreparedReport): void => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.contributions });
    },
  });
}
