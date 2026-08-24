import { useCallback } from 'react';

import { ApiRequestError } from '@/api';
import { PageSkeleton } from '@/components/ui/PageSkeleton';
import { usePageTitle } from '@/hooks/usePageTitle';

import { InsightCard } from './InsightCard';
import { useInsightList } from './useInsightList';

import styles from './InsightsListPage.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The insight list could not be loaded. Try again.';
}

export function InsightsListPage() {
  usePageTitle('Insights');
  const insightsQuery = useInsightList();

  const handleRetry = useCallback((): void => {
    void insightsQuery.refetch();
  }, [insightsQuery]);

  if (insightsQuery.isPending) {
    return <PageSkeleton label="the insight list" />;
  }

  if (insightsQuery.isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(insightsQuery.error)}</p>
        <button type="button" className={styles.retry} onClick={handleRetry}>
          Try again
        </button>
      </div>
    );
  }

  const { insights } = insightsQuery.data;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Insights</h1>
        <p className={styles.lead}>
          Snapshots of a figure or a day. Each insight carries the counts it rests on. Start a
          snapshot from Overview. Colleagues attach notes to the same finding; this is not a public
          forum.
        </p>
      </header>

      {insights.length === 0 ? (
        <p className={styles.empty}>
          No insight has been started yet. Open Overview, pick a collected day, a key figure, or a
          breakdown row, and start a snapshot there.
        </p>
      ) : (
        <ul className={styles.list}>
          {insights.map((insight) => (
            <li key={insight.id}>
              <InsightCard insight={insight} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
