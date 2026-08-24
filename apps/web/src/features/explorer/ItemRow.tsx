import { Link } from 'react-router-dom';

import { platformLabel, reviewLabel, type ExplorerItem, type ExplorerItemImage } from '@/api';
import { SafeImage } from '@/components/ui/SafeImage';
import { StatusPill, type StatusIndicator } from '@/components/ui/StatusPill';

import { classificationLabel, itemSeverityLabel, itemTypeLabel } from './item-copy';

import styles from './ItemsTable.module.css';

interface ItemRowProps {
  item: ExplorerItem;
}

/**
 * Both the fixture vocabulary (`pending`) and the live service vocabulary
 * (`model_only`, `pending_review`, `disputed`, `needs_context`) map onto the
 * three visual states. An unknown future state renders as pending rather than
 * as a false confirmation.
 */
const REVIEW_INDICATOR: Record<string, StatusIndicator> = {
  confirmed: 'ok',
  pending: 'pending',
  pending_review: 'pending',
  model_only: 'pending',
  corrected: 'degraded',
  disputed: 'degraded',
  needs_context: 'degraded',
};

/**
 * Dense table labels. The full review phrase stays on `title` for hover and
 * assistive tech that reads the accessible name from the pill text plus title.
 */
const REVIEW_TABLE_LABEL: Record<string, string> = {
  pending: 'Awaiting review',
  pending_review: 'Awaiting review',
  model_only: 'Model only',
  confirmed: 'Confirmed',
  corrected: 'Corrected',
  disputed: 'Disputed',
  needs_context: 'Needs context',
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
        <Link className={styles.itemId} to={`/app/explorer/${encodeURIComponent(item.id)}`}>
          item {item.id}
        </Link>
      </th>
      <td>{item.platformDisplay ?? platformLabel(item.platform)}</td>
      <td className={styles.context}>{item.containerTitle ?? 'No public context'}</td>
      <td className={styles.excerptCell}>
        {item.image !== undefined && item.image !== null ? (
          <ImageContent image={item.image} />
        ) : (
          <p className={styles.excerpt}>{item.redactedExcerpt ?? 'No permitted excerpt'}</p>
        )}
      </td>
      <td className={styles.classification}>{classificationLabel(item.classification)}</td>
      <td>{itemTypeLabel(item.hateType)}</td>
      <td className={styles.numeric}>
        {item.modelScore === null ? '—' : item.modelScore.toFixed(2)}
      </td>
      <td className={styles.severity}>{itemSeverityLabel(item.severity)}</td>
      <td className={styles.review}>
        <div className={styles.reviewBody}>
          <StatusPill
            indicator={REVIEW_INDICATOR[item.reviewState] ?? 'pending'}
            label={REVIEW_TABLE_LABEL[item.reviewState] ?? fullReview}
            title={fullReview}
          />
          {item.reviewNote !== null && <p className={styles.note}>{item.reviewNote}</p>}
        </div>
      </td>
    </tr>
  );
}

function ImageContent({ image }: { image: ExplorerItemImage }) {
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
      <SafeImage src={image.imageSrc} alt={image.altText} />
    </div>
  );
}
