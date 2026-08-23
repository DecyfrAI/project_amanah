import { useCallback, useState } from 'react';

import { platformLabel, reviewLabel, type ExplorerItem, type ExplorerItemImage } from '@/api';
import { StatusPill, type StatusIndicator } from '@/components/ui/StatusPill';

import { classificationLabel, itemSeverityLabel, itemTypeLabel } from './item-copy';

import styles from './ItemsTable.module.css';

interface ItemRowProps {
  item: ExplorerItem;
}

const REVIEW_INDICATOR: Record<ExplorerItem['reviewState'], StatusIndicator> = {
  confirmed: 'ok',
  pending: 'pending',
  corrected: 'degraded',
};

/**
 * Dense table labels. The full review phrase stays on `title` for hover and
 * assistive tech that reads the accessible name from the pill text plus title.
 */
const REVIEW_TABLE_LABEL: Record<ExplorerItem['reviewState'], string> = {
  pending: 'Awaiting review',
  confirmed: 'Confirmed',
  corrected: 'Corrected',
};

/**
 * One collected item as a table row.
 *
 * The excerpt is synthetic wording shown in full. There is no author, no handle
 * and no link to a person: person-level views are out of scope.
 */
export function ItemRow({ item }: ItemRowProps) {
  const fullReview = reviewLabel(item.reviewState);

  return (
    <tr>
      <th scope="row" className={styles.identity}>
        <span className={styles.date}>{item.date}</span>
        <span className={styles.itemId}>item {item.id}</span>
      </th>
      <td>{platformLabel(item.platform)}</td>
      <td className={styles.context}>{item.containerTitle}</td>
      <td className={styles.excerptCell}>
        {item.image !== undefined && item.image !== null ? (
          <ImageContent itemId={item.id} image={item.image} />
        ) : (
          <p className={styles.excerpt}>{item.redactedExcerpt}</p>
        )}
      </td>
      <td className={styles.classification}>{classificationLabel(item.classification)}</td>
      <td>{itemTypeLabel(item.hateType)}</td>
      <td className={styles.numeric}>{item.modelScore.toFixed(2)}</td>
      <td className={styles.severity}>{itemSeverityLabel(item.severity)}</td>
      <td className={styles.review}>
        <div className={styles.reviewBody}>
          <StatusPill
            indicator={REVIEW_INDICATOR[item.reviewState]}
            label={REVIEW_TABLE_LABEL[item.reviewState]}
            title={fullReview}
          />
          {item.reviewNote !== null && <p className={styles.note}>{item.reviewNote}</p>}
        </div>
      </td>
    </tr>
  );
}

function ImageContent({ itemId, image }: { itemId: string; image: ExplorerItemImage }) {
  const [revealed, setRevealed] = useState(false);
  const handleToggle = useCallback((): void => {
    setRevealed((current) => !current);
  }, []);

  return (
    <div className={styles.imageBlock}>
      <p className={styles.excerpt}>{image.formNote}</p>
      <dl className={styles.imageMeta}>
        <div>
          <dt>File</dt>
          <dd>
            {image.filename} · {image.byteSize.toLocaleString('en')} bytes · {image.mime}
          </dd>
        </div>
      </dl>
      <button
        type="button"
        className={styles.reveal}
        aria-expanded={revealed}
        aria-controls={`${itemId}-image`}
        onClick={handleToggle}
      >
        {revealed ? 'Hide image' : 'Reveal image'}
      </button>
      <img
        id={`${itemId}-image`}
        className={revealed ? styles.thumb : `${styles.thumb} ${styles.thumbBlurred}`}
        src={image.imageSrc}
        alt={image.altText}
      />
    </div>
  );
}
