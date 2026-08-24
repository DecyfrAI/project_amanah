import { useMutation, type UseMutationResult } from '@tanstack/react-query';

import { apiClient, type CreateResearchReportRequest, type ResearchReport } from '@/api';

/**
 * Freeze a research-report snapshot.
 *
 * Deliberately not a query: generating a report is an action that records an
 * audit event server-side, so it must not be retried or refetched on a window
 * focus. The snapshot it returns is immutable.
 */
export function useCreateResearchReport(): UseMutationResult<
  ResearchReport,
  Error,
  CreateResearchReportRequest
> {
  return useMutation({
    mutationFn: (input: CreateResearchReportRequest) => apiClient.createResearchReport(input),
  });
}

export function useDownloadReportCsv(): UseMutationResult<string, Error, ResearchReport> {
  return useMutation({
    mutationFn: (report: ResearchReport) => apiClient.downloadResearchReportCsv(report),
  });
}
