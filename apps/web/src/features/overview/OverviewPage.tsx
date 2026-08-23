import { DashboardView } from '@/features/dashboard/DashboardView';
import { usePageTitle } from '@/hooks/usePageTitle';

/**
 * The dashboard as a reviewer sees it, inside the workspace shell.
 *
 * Identical figures to the public route, with the drill-down into supporting
 * records added, since that is one of the things a session buys.
 */
export function OverviewPage() {
  usePageTitle('Overview');

  return (
    <DashboardView
      heading="Overview"
      lead="What the monitored sample contains for this window, and how the likely-hate rate is moving inside it. Any collected day, key figure, or breakdown row can become a snapshot on Insights for colleagues to discuss."
      explorerPath="/app/explorer"
    />
  );
}
