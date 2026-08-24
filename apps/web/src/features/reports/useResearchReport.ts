import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  apiClient,
  queryKeys,
  type CreateResearchReportInput,
  type WireResearchReport,
} from '@/api';

/**
 * Creates one immutable research-report snapshot (`POST /v1/research-reports`).
 *
 * The snapshot is frozen server-side against the filters sent with it, so the
 * report cannot drift from the query behind it. A failure surfaces to the page;
 * nothing here substitutes a fixture snapshot.
 */
export function useCreateResearchReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateResearchReportInput) => apiClient.createResearchReport(input),
    onSuccess: (report: WireResearchReport): void => {
      queryClient.setQueryData(queryKeys.researchReport(report.id), report);
    },
  });
}

/**
 * Downloads the aggregate CSV for a stored snapshot.
 *
 * Aggregate counts and denominators only — never item-level rows. The browser
 * saves the blob the authenticated API returned; the URL is revoked straight
 * after so a signed download link does not linger in the document.
 */
export function useDownloadResearchReportCsv() {
  return useMutation({
    mutationFn: async (report: WireResearchReport): Promise<void> => {
      const blob = await apiClient.downloadResearchReportCsv(report.id);
      const href = URL.createObjectURL(blob);
      try {
        const link = document.createElement('a');
        link.href = href;
        link.download = `research-report-${report.id}.csv`;
        document.body.append(link);
        link.click();
        link.remove();
      } finally {
        URL.revokeObjectURL(href);
      }
    },
  });
}
