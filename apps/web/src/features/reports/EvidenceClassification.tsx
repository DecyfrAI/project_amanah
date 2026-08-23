import type { ImageClassification } from '@/api';
import { hateTypeLabel, severityLabel } from '@/api';
import { StatusPill } from '@/components/ui/StatusPill';

import styles from './EvidenceClassification.module.css';

interface EvidenceClassificationProps {
  readonly result: ImageClassification;
}

function tierIndicator(
  tier: ImageClassification['confidence_tier'],
): 'ok' | 'pending' | 'degraded' {
  if (tier === 'high') {
    return 'ok';
  }
  if (tier === 'medium') {
    return 'pending';
  }
  return 'degraded';
}

/**
 * Spec §9.5 fields for an uploaded screenshot. The model score is a score,
 * not certainty. A dataset annotation is labeled as an annotation.
 */
export function EvidenceClassification({ result }: EvidenceClassificationProps) {
  return (
    <section className={styles.card} aria-labelledby="image-class-heading">
      <div className={styles.head}>
        <h3 className={styles.heading} id="image-class-heading">
          Image classification
        </h3>
        <StatusPill
          indicator={result.classification === 'likely_hate' ? 'degraded' : 'ok'}
          label={
            result.classification === 'likely_hate'
              ? 'Classified as likely anti-Muslim hate'
              : 'Classified as not hate'
          }
        />
        <StatusPill
          indicator={tierIndicator(result.confidence_tier)}
          label={`${result.confidence_tier} confidence`}
        />
      </div>
      <p className={styles.disclosure}>{result.disclosure}</p>
      <dl className={styles.facts}>
        <div>
          <dt>Relevance</dt>
          <dd>{result.relevance.replaceAll('_', ' ')}</dd>
        </div>
        <div>
          <dt>Stance</dt>
          <dd>{result.stance.replaceAll('_', ' ')}</dd>
        </div>
        <div>
          <dt>Hate types</dt>
          <dd>{result.hate_types.map((type) => hateTypeLabel(type)).join(', ')}</dd>
        </div>
        <div>
          <dt>Severity</dt>
          <dd>
            {result.severity === null ? 'Not assigned' : severityLabel(String(result.severity))}
          </dd>
        </div>
        <div>
          <dt>Model score</dt>
          <dd>
            {result.score.toFixed(2)}, {result.model_name} {result.model_version}. Not a measure of
            certainty.
          </dd>
        </div>
        <div>
          <dt>Review</dt>
          <dd>
            {result.review_required
              ? 'Required. Severity 3 stays in the review queue.'
              : 'Eligible. A person has not confirmed this yet.'}
          </dd>
        </div>
      </dl>
      <p className={styles.rationale}>{result.rationale}</p>
      {result.dataset_annotation !== null && (
        <p className={styles.annotation}>
          Original fixture annotation:{' '}
          {result.dataset_annotation.hate_types.map(hateTypeLabel).join(', ')}, severity{' '}
          {result.dataset_annotation.severity}. That label is a dataset annotation, not an Amanah
          prediction and not a human review.
        </p>
      )}
    </section>
  );
}
