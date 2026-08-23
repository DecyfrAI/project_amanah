import { MockupNotice } from '@/components/ui/MockupNotice';
import { InfoTip } from '@/components/ui/InfoTip';
import { usePageTitle } from '@/hooks/usePageTitle';

import { ImageExampleCatalog } from '@/features/reports/ImageExampleCatalog';

import { ImageLabelForm } from './ImageLabelForm';
import { QueueRow } from './QueueRow';
import { QUEUE_FIGURES, QUEUE_ITEMS } from './mock';

import styles from './ReviewPage.module.css';

/**
 * Review queue, laid out from local constants for design review.
 *
 * The queue is where a machine prediction becomes a human judgment, so the two
 * things this layout has to get right are that a decision appends beside the
 * prediction rather than replacing it, and that the classification stays a
 * proposal until a person decides. Both are stated in the page, not left to a
 * reader to infer. Nothing here is wired: `POST /v1/review/tasks/{id}/decisions`
 * does not exist for this frontend yet, so the decision controls are disabled
 * and say why.
 */
export function ReviewPage() {
  usePageTitle('Review queue');

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

      <MockupNotice detail="The six items below, their scores, and the queue figures are illustrations of a queue, not a queue." />

      <section className={styles.figures} aria-labelledby="queue-figures-heading">
        <div className={styles.headingRow}>
          <h2 id="queue-figures-heading" className={styles.sectionHeading}>
            Queue at a glance
          </h2>
          <InfoTip label="Queue at a glance">
            Counts for this mock queue. A review appends a decision beside the model score. The
            original prediction stays visible.
          </InfoTip>
        </div>
        <div className={styles.figureGrid}>
          {QUEUE_FIGURES.map((figure) => (
            <article
              key={figure.id}
              className={styles.figureCard}
              aria-labelledby={`${figure.id}-label`}
            >
              <div className={styles.figureHead}>
                <h3 id={`${figure.id}-label`} className={styles.figureLabel}>
                  {figure.label}
                </h3>
                <InfoTip label={figure.label} placement="card">
                  {figure.definition}
                </InfoTip>
              </div>
              <p className={styles.figureValue}>{figure.value}</p>
              <p className={styles.figureBasis}>{figure.basis}</p>
            </article>
          ))}
        </div>
        <p className={styles.caveat}>
          The Mastodon connector collected nothing on 3 of the 14 days in this window. Those days
          are a gap in collection, not three days without anything to find, and they are excluded
          from every denominator above.
        </p>
      </section>

      <section className={styles.queue} aria-labelledby="queue-heading">
        <h2 id="queue-heading" className={styles.sectionHeading}>
          Awaiting a decision
        </h2>
        <p className={styles.queueNote}>
          Showing 6 of the 34 items awaiting review. Every label below is the model's proposal, not
          a finding, and every score is a model score rather than a measure of how certain anything
          is.
        </p>
        <ul className={styles.queueList}>
          {QUEUE_ITEMS.map((item) => (
            <QueueRow key={item.id} item={item} />
          ))}
        </ul>
      </section>

      <ImageLabelForm />
      <ImageExampleCatalog />
    </div>
  );
}
