import { Link } from 'react-router-dom';

import { StatusPill } from '@/components/ui/StatusPill';
import { reportPlatformFromLabel } from '@/features/reports/prepare-report-draft';

import { QUEUE_REASON_LABELS, type QueueItem } from './mock';

import styles from './QueueRow.module.css';

interface QueueRowProps {
  item: QueueItem;
}

function formatObserved(timestamp: string): string {
  return new Date(timestamp).toISOString().replace('T', ' ').slice(0, 16).concat(' UTC');
}

/**
 * One item awaiting a decision.
 *
 * The excerpt is synthetic wording shown in full. The severity band is
 * deliberately plain text, since brand system 4 reserves red for harm a person
 * has confirmed and nothing in this queue has been confirmed yet.
 */
export function QueueRow({ item }: QueueRowProps) {
  const headingId = `${item.id}-container`;
  const decisionNoteId = `${item.id}-decision-note`;

  return (
    <li className={styles.row}>
      <article aria-labelledby={headingId}>
        <div className={styles.top}>
          <div className={styles.identity}>
            <h3 id={headingId} className={styles.container}>
              {item.container}
            </h3>
            <p className={styles.meta}>
              {item.platform} · item {item.id} · observed {formatObserved(item.observedAt)}
            </p>
          </div>
          <StatusPill indicator="pending" label="Awaiting review" />
        </div>

        <dl className={styles.facts}>
          <div className={styles.fact}>
            <dt className={styles.term}>Proposed label</dt>
            <dd className={styles.value}>{item.proposedLabel}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Model score</dt>
            <dd className={styles.value}>
              {item.modelScore.toFixed(2)} ({item.confidenceTier.toLowerCase()} confidence)
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Severity band</dt>
            <dd className={styles.value}>
              {item.severityBand} of 3, {item.severityLabel}
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Why it is queued</dt>
            <dd className={styles.value}>{QUEUE_REASON_LABELS[item.reason]}</dd>
          </div>
        </dl>

        <div className={styles.excerptBlock}>
          <p className={styles.excerpt}>{item.excerpt}</p>
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.primaryAction}
            disabled
            aria-describedby={decisionNoteId}
          >
            Confirm label
          </button>
          <button
            type="button"
            className={styles.action}
            disabled
            aria-describedby={decisionNoteId}
          >
            Correct label
          </button>
          <button
            type="button"
            className={styles.action}
            disabled
            aria-describedby={decisionNoteId}
          >
            Skip for now
          </button>
          <p id={decisionNoteId} className={styles.actionNote}>
            Decisions are unavailable: recording one needs the review API, which is not connected
            yet.
          </p>
        </div>

        <p className={styles.reportCue}>
          If this content should go to a platform, prepare a report. That opens Reports. It does not
          send anything, and it is not a review decision.
        </p>
        <Link
          className={styles.reportLink}
          to={`/app/reports?platform=${reportPlatformFromLabel(item.platform)}&item=${encodeURIComponent(item.id)}`}
        >
          Prepare a report
        </Link>

        <p className={styles.provenance}>{item.modelVersion}</p>
      </article>
    </li>
  );
}
