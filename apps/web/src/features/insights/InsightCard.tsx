import { Link } from 'react-router-dom';

import type { Insight } from '@/api';
import { StatusPill } from '@/components/ui/StatusPill';

import { insightKind, insightProvenance, insightSourceLine } from './insight-copy';

import styles from './InsightCard.module.css';

interface InsightCardProps {
  insight: Insight;
}

/**
 * One insight on the list, using the same card chrome as the old item cards:
 * a heading, a quiet meta line, a recessed summary, and a labelled metric row.
 * The fields stay insight fields. There is no excerpt and no person.
 */
export function InsightCard({ insight }: InsightCardProps) {
  const kind = insightKind(insight);
  const sources = insightSourceLine(insight);

  return (
    <article className={styles.card} aria-labelledby={`${insight.id}-title`}>
      <header className={styles.head}>
        <div className={styles.headingRow}>
          <h2 className={styles.heading} id={`${insight.id}-title`}>
            <Link className={styles.titleLink} to={`/app/insights/${insight.id}`}>
              {insight.title}
            </Link>
          </h2>
          <StatusPill indicator={kind.indicator} label={kind.label} />
        </div>
        <p className={styles.meta}>
          {insight.window.from} to {insight.window.to} · {sources} · {insight.id}
        </p>
      </header>

      <div className={styles.well}>
        <p className={styles.summary}>{insight.summary}</p>
      </div>

      <dl className={styles.facts}>
        <div className={styles.fact}>
          <dt>Window</dt>
          <dd>
            {insight.window.from} to {insight.window.to}
          </dd>
        </div>
        <div className={styles.fact}>
          <dt>Relevant</dt>
          <dd>
            {insight.coverage.itemsRelevant.toLocaleString('en-GB')} of{' '}
            {insight.coverage.itemsObserved.toLocaleString('en-GB')}
          </dd>
        </div>
        <div className={styles.fact}>
          <dt>Sources</dt>
          <dd>{sources}</dd>
        </div>
        <div className={styles.fact}>
          <dt>Cited figures</dt>
          <dd>{insight.facts.length.toLocaleString('en-GB')}</dd>
        </div>
      </dl>

      <p className={styles.provenance}>{insightProvenance(insight)}</p>
    </article>
  );
}
