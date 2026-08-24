import { useCallback, useState } from 'react';

import { ApiRequestError, type ReviewDecisionEntry, type ReviewTask } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';
import { PageSkeleton } from '@/components/ui/PageSkeleton';
import { usePageTitle } from '@/hooks/usePageTitle';

import { ImageExampleCatalog } from '@/features/reports/ImageExampleCatalog';

import { ImageLabelForm } from './ImageLabelForm';
import { QueueRow } from './QueueRow';
import { useReviewQueue } from './useReviewQueue';

import styles from './ReviewPage.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The review queue could not be loaded. Try again.';
}

/**
 * Review queue.
 *
 * The two things this layout has to get right are that a decision appends beside
 * the prediction rather than replacing it, and that the classification stays a
 * proposal until a person decides. Both are stated in the page, not left to a
 * reader to infer.
 */
export function ReviewPage() {
  usePageTitle('Review queue');
  const queue = useReviewQueue();
  // Decision history for tasks decided in this session, keyed by task id. The
  // list endpoint carries tasks only; a decision returns the full history.
  const [decisions, setDecisions] = useState<Record<string, readonly ReviewDecisionEntry[]>>({});
  const [claimed, setClaimed] = useState<Record<string, ReviewTask>>({});

  const handleDecided = useCallback(
    (detail: { task: ReviewTask; decisions: readonly ReviewDecisionEntry[] }): void => {
      setDecisions((current) => ({ ...current, [detail.task.id]: detail.decisions }));
      setClaimed((current) => ({ ...current, [detail.task.id]: detail.task }));
    },
    [],
  );

  const handleRetry = useCallback((): void => {
    void queue.refetch();
  }, [queue]);

  if (queue.isPending) {
    return <PageSkeleton label="the review queue" />;
  }

  if (queue.isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(queue.error)}</p>
        <button type="button" className={styles.retry} onClick={handleRetry}>
          Try again
        </button>
      </div>
    );
  }

  const { items, totals } = queue.data;
  const agreementBasis =
    totals.decided === 0
      ? 'No decision has been recorded yet.'
      : `${totals.confirmed} confirmations of ${totals.decided} decided items`;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Review queue</h1>
        <p className={styles.lead}>
          Items the pipeline could not settle on its own, ordered by what most needs a person. A
          review appends a decision beside the model's prediction. It never overwrites it, so a
          later reader can still see what the model proposed and who disagreed.
        </p>
      </header>

      <section className={styles.figures} aria-labelledby="queue-figures-heading">
        <div className={styles.headingRow}>
          <h2 id="queue-figures-heading" className={styles.sectionHeading}>
            Queue at a glance
          </h2>
          <InfoTip label="Queue at a glance">
            Counts for this queue. A review appends a decision beside the model score. The original
            prediction stays visible.
          </InfoTip>
        </div>
        <div className={styles.figureGrid}>
          <QueueFigure
            id="awaiting"
            label="Items awaiting review"
            value={String(totals.open)}
            basis={
              totals.classified_in_window === 0
                ? `${totals.open} open in this queue`
                : `${totals.open} of ${totals.classified_in_window.toLocaleString()} classified items in the window`
            }
            definition="Classified items the pipeline routed to a person, out of everything it classified in the window."
          />
          <QueueFigure
            id="decided"
            label="Decisions recorded"
            value={String(totals.decided)}
            basis={`${totals.decided} of ${String(items.length)} items shown`}
            definition="Items a reviewer has settled. A decision appends beside the prediction and never rewrites it."
          />
          <QueueFigure
            id="agreement"
            label="Reviewers agreed with the model"
            value={
              totals.decided === 0
                ? 'Not yet'
                : `${totals.confirmed} of ${totals.decided} (${Math.round((totals.confirmed / totals.decided) * 100)}%)`
            }
            basis={agreementBasis}
            definition="Decisions that confirmed the proposed label rather than correcting it. Agreement is not accuracy: both a reviewer and the model can be wrong."
          />
        </div>
      </section>

      <section className={styles.queue} aria-labelledby="queue-heading">
        <h2 id="queue-heading" className={styles.sectionHeading}>
          Awaiting a decision
        </h2>
        <p className={styles.queueNote}>
          Every label below is the model's proposal, not a finding, and every score is a model score
          rather than a measure of how certain anything is.
        </p>
        {items.length === 0 ? (
          <p className={styles.empty}>
            Nothing is waiting for a decision. An item arrives here when the pipeline cannot settle
            it on its own.
          </p>
        ) : (
          <ul className={styles.queueList} aria-labelledby="queue-heading">
            {items.map((task) => (
              <QueueRow
                key={task.id}
                task={claimed[task.id] ?? task}
                decisions={decisions[task.id] ?? []}
                onDecided={handleDecided}
              />
            ))}
          </ul>
        )}
      </section>

      <ImageLabelForm />
      <ImageExampleCatalog />
    </div>
  );
}

interface QueueFigureProps {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  readonly basis: string;
  readonly definition: string;
}

function QueueFigure({ id, label, value, basis, definition }: QueueFigureProps) {
  return (
    <article className={styles.figureCard} aria-labelledby={`${id}-label`}>
      <div className={styles.figureHead}>
        <h3 id={`${id}-label`} className={styles.figureLabel}>
          {label}
        </h3>
        <InfoTip label={label} placement="card">
          {definition}
        </InfoTip>
      </div>
      <p className={styles.figureValue}>{value}</p>
      <p className={styles.figureBasis}>{basis}</p>
    </article>
  );
}
