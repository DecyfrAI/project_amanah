import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiRequestError, platformLabel, reviewLabel, type ExplorerItemDetail } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';
import { SafeImage } from '@/components/ui/SafeImage';
import { usePageTitle } from '@/hooks/usePageTitle';

import { classificationLabel, itemSeverityLabel, itemTypeLabel } from './item-copy';
import { useItem } from './useItem';

import styles from './ItemDetailPage.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'This item could not be loaded. Try again.';
}

/**
 * One collected item, with the disclosure a classification must never be shown
 * without (F-S8).
 *
 * There is no author, handle, or link to a person anywhere on this page:
 * person-level views are out of scope. What it adds over the Explorer row is the
 * provenance a reader needs to judge the label — the score, the versions that
 * produced it, when it ran, the model's own rationale, and what this sample
 * cannot support.
 */
export function ItemDetailPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const id = itemId ?? '';
  const itemQuery = useItem(id);
  usePageTitle(itemQuery.data === undefined ? 'Item' : `Item ${itemQuery.data.id}`);

  const handleRetry = useCallback((): void => {
    void itemQuery.refetch();
  }, [itemQuery]);

  if (id === '') {
    return (
      <div className={styles.error} role="alert">
        <p>No item was specified.</p>
      </div>
    );
  }

  if (itemQuery.isPending) {
    return <p className={styles.status}>Loading item</p>;
  }

  if (itemQuery.isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(itemQuery.error)}</p>
        <button type="button" className={styles.retry} onClick={handleRetry}>
          Try again
        </button>
      </div>
    );
  }

  return <ItemDetail item={itemQuery.data} />;
}

function ItemDetail({ item }: { item: ExplorerItemDetail }) {
  return (
    <article className={styles.page}>
      <Link className={styles.backLink} to="/app/explorer">
        Back to Explorer
      </Link>

      <header className={styles.header}>
        <p className={styles.kicker}>Collected item</p>
        <h1 className={styles.title}>{item.containerTitle ?? 'No public context recorded'}</h1>
        <p className={styles.meta}>
          {item.platformDisplay ?? platformLabel(item.platform)} · {item.date} · {item.id}
        </p>
      </header>

      <section className={styles.card} aria-labelledby="content-heading">
        <h2 id="content-heading" className={styles.sectionHeading}>
          What was collected
        </h2>
        {item.image !== undefined && item.image !== null ? (
          <SafeImage
            src={item.image.imageSrc}
            alt={item.image.altText}
            note={`${item.image.filename} · ${item.image.byteSize.toLocaleString('en-GB')} bytes · ${item.image.mime}`}
          />
        ) : (
          <p className={styles.excerpt}>
            {item.redactedExcerpt ?? 'No excerpt is permitted for this item.'}
          </p>
        )}
        {item.containerUrl !== null && (
          <div className={styles.actions}>
            <a
              className={styles.action}
              href={item.containerUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open the original source (opens in a new tab)
            </a>
          </div>
        )}
      </section>

      <section className={styles.card} aria-labelledby="classification-heading">
        <div className={styles.headingRow}>
          <h2 id="classification-heading" className={styles.sectionHeading}>
            Classification
          </h2>
          <InfoTip label="Classification">
            A model score is a score on the model&apos;s own scale. It is not a probability and not
            a measure of certainty. Until a reviewer confirms it, this is a proposal.
          </InfoTip>
        </div>

        <dl className={styles.facts}>
          <div className={styles.fact}>
            <dt className={styles.term}>Proposed label</dt>
            <dd className={styles.value}>{classificationLabel(item.classification)}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Type of harm</dt>
            <dd className={styles.value}>{itemTypeLabel(item.hateType)}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Severity</dt>
            <dd className={styles.value}>{itemSeverityLabel(item.severity)}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Model score</dt>
            <dd className={styles.value}>
              {item.modelScore === null ? 'Not classified' : item.modelScore.toFixed(2)}
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Review state</dt>
            <dd className={styles.value}>{reviewLabel(item.reviewState)}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Classified at</dt>
            <dd className={styles.value}>{item.inferredAt ?? 'Not classified'}</dd>
          </div>
        </dl>

        {item.rationale !== null && (
          <>
            <h3 className={styles.term}>Model rationale</h3>
            <p className={styles.disclosure}>{item.rationale}</p>
          </>
        )}
      </section>

      <section className={styles.card} aria-labelledby="disclosure-heading">
        <div className={styles.headingRow}>
          <h2 id="disclosure-heading" className={styles.sectionHeading}>
            Model disclosure
          </h2>
          <InfoTip label="Model disclosure">
            Which model, prompt, and taxonomy version produced this label. A label without its
            versions cannot be reproduced or challenged.
          </InfoTip>
        </div>
        <dl className={styles.facts}>
          <div className={styles.fact}>
            <dt className={styles.term}>Model</dt>
            <dd className={styles.value}>{item.modelName ?? 'Not classified'}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Model version</dt>
            <dd className={styles.value}>{item.modelVersion ?? 'Not classified'}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Prompt version</dt>
            <dd className={styles.value}>{item.promptVersion ?? 'Not classified'}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Taxonomy version</dt>
            <dd className={styles.value}>{item.taxonomyVersion ?? 'Not classified'}</dd>
          </div>
        </dl>
      </section>

      {item.dataset !== undefined && item.dataset !== null && (
        <section className={styles.card} aria-labelledby="dataset-heading">
          <div className={styles.headingRow}>
            <h2 id="dataset-heading" className={styles.sectionHeading}>
              Dataset provenance
            </h2>
            <InfoTip label="Dataset provenance">
              This row came from a reviewed open datapack, so its public platform reads N/A. The
              dataset&apos;s own labels are annotations, never Amanah findings.
            </InfoTip>
          </div>
          <dl className={styles.facts}>
            <div className={styles.fact}>
              <dt className={styles.term}>Provider</dt>
              <dd className={styles.value}>{item.dataset.provider}</dd>
            </div>
            <div className={styles.fact}>
              <dt className={styles.term}>Dataset</dt>
              <dd className={styles.value}>
                {item.dataset.name} {item.dataset.version}
              </dd>
            </div>
            <div className={styles.fact}>
              <dt className={styles.term}>Licence</dt>
              <dd className={styles.value}>{item.dataset.licenseId ?? 'Not recorded'}</dd>
            </div>
          </dl>
        </section>
      )}

      <section className={styles.card} aria-labelledby="limitations-heading">
        <h2 id="limitations-heading" className={styles.sectionHeading}>
          Limitations
        </h2>
        <p className={styles.disclosure}>{item.samplingDisclosure}</p>
        {item.limitations.length > 0 && (
          <ul className={styles.list}>
            {item.limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.card} aria-labelledby="actions-heading">
        <h2 id="actions-heading" className={styles.sectionHeading}>
          Act on this item
        </h2>
        <p className={styles.disclosure}>
          Preparing a report writes wording for you to file yourself on the platform&apos;s own
          form. Amanah never submits a report.
        </p>
        <div className={styles.actions}>
          <Link className={styles.action} to={`/app/reports?item=${encodeURIComponent(item.id)}`}>
            Prepare a report
          </Link>
        </div>
      </section>
    </article>
  );
}
