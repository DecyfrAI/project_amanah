import { useCallback } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';

import { ApiRequestError, type Insight } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';
import { StatusPill } from '@/components/ui/StatusPill';
import { DiscussionPanel } from '@/features/discussion/DiscussionPanel';
import { usePageTitle } from '@/hooks/usePageTitle';

import cardStyles from './InsightCard.module.css';
import { insightKind, insightProvenance, insightSourceLine } from './insight-copy';
import { useInsight } from './useInsight';

import styles from './InsightPage.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'This insight could not be loaded. Try again.';
}

export function InsightPage() {
  const { insightId } = useParams<{ insightId: string }>();
  const location = useLocation();
  const id = insightId ?? '';
  const insightQuery = useInsight(id);
  usePageTitle(insightQuery.data?.title ?? 'Insight');
  const wasJustCreated = (location.state as { created?: unknown } | null)?.created === true;

  const handleRetry = useCallback((): void => {
    void insightQuery.refetch();
  }, [insightQuery]);

  if (id.length === 0) {
    return (
      <div className={styles.error} role="alert">
        <p>No insight was specified.</p>
      </div>
    );
  }

  if (insightQuery.isPending) {
    return <p className={styles.status}>Loading insight</p>;
  }

  if (insightQuery.isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(insightQuery.error)}</p>
        <button type="button" className={styles.retry} onClick={handleRetry}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <article className={styles.page}>
      {wasJustCreated && (
        <output className={styles.createdNotice} aria-live="polite">
          Saved. This snapshot was added to Insights, where colleagues can find it and attach notes.
        </output>
      )}
      <Link className={styles.backLink} to="/app/insights">
        View all insights
      </Link>
      <InsightHeader insight={insightQuery.data} />
      <CitedFigures insight={insightQuery.data} />
      <DiscussionPanel insightId={insightQuery.data.id} />
    </article>
  );
}

function InsightHeader({ insight }: { insight: Insight }) {
  const kind = insightKind(insight);
  const sources = insightSourceLine(insight);

  return (
    <header className={cardStyles.card}>
      <div className={cardStyles.head}>
        <div className={cardStyles.headingRow}>
          <p className={styles.kicker}>
            {insight.generation.model === 'viewer-snapshot' ? 'Snapshot' : 'Insight'}
          </p>
          <StatusPill indicator={kind.indicator} label={kind.label} />
        </div>
        <h1 className={styles.title}>{insight.title}</h1>
        <p className={cardStyles.meta}>
          {insight.window.from} to {insight.window.to} ({insight.window.timezone}) · {sources} ·{' '}
          {insight.id}
        </p>
      </div>

      <div className={cardStyles.well}>
        <p className={cardStyles.summary}>{insight.summary}</p>
      </div>

      <dl className={cardStyles.facts}>
        <div className={cardStyles.fact}>
          <dt>Window</dt>
          <dd>
            {insight.window.from} to {insight.window.to}
          </dd>
        </div>
        <div className={cardStyles.fact}>
          <dt>Relevant</dt>
          <dd>
            {insight.coverage.itemsRelevant.toLocaleString('en-GB')} of{' '}
            {insight.coverage.itemsObserved.toLocaleString('en-GB')}
          </dd>
        </div>
        <div className={cardStyles.fact}>
          <dt>Sources</dt>
          <dd>{sources}</dd>
        </div>
        <div className={cardStyles.fact}>
          <dt>Cited figures</dt>
          <dd>{insight.facts.length.toLocaleString('en-GB')}</dd>
        </div>
      </dl>

      {insight.coverage.warnings.length > 0 && (
        <ul className={styles.warnings}>
          {insight.coverage.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      <p className={cardStyles.provenance}>{insightProvenance(insight)}</p>
    </header>
  );
}

function CitedFigures({ insight }: { insight: Insight }) {
  return (
    <section className={styles.facts} aria-labelledby="facts-heading">
      <div className={styles.headingRow}>
        <h2 id="facts-heading" className={styles.sectionHeading}>
          Cited figures
        </h2>
        <InfoTip label="Cited figures">
          Stored numbers this thread is about. A generated summary may explain them. It never
          produces them.
        </InfoTip>
      </div>
      <ul className={styles.factList}>
        {insight.facts.map((fact) => (
          <li key={fact.id} className={cardStyles.card}>
            <div className={cardStyles.well}>
              <p className={cardStyles.summary}>{fact.claim}</p>
            </div>
            <dl className={cardStyles.facts}>
              <div className={cardStyles.fact}>
                <dt>Count</dt>
                <dd>
                  {fact.numerator.toLocaleString('en-GB')} of{' '}
                  {fact.denominator.toLocaleString('en-GB')}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </section>
  );
}
