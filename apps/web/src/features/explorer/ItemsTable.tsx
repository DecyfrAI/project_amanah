import type { ExplorerItem } from '@/api';

import { ItemRow } from './ItemRow';

import styles from './ItemsTable.module.css';

interface ItemsTableProps {
  items: readonly ExplorerItem[];
}

/**
 * The records behind the figures, as a scanable table.
 *
 * Filters stay in the URL and in the bar above. This table is the list those
 * filters produce: one row per reviewed example, with the excerpt shown in full.
 */
export function ItemsTable({ items }: ItemsTableProps) {
  return (
    <div className={styles.frame}>
      <div className={styles.scroller}>
        <table className={styles.table}>
          <caption className={styles.caption}>
            Reviewed examples matching the current filters. Comment rows show synthetic wording.
            Image rows show form and file metadata. A pending row is a model proposal, not a
            finding. A reviewed row keeps the original prediction beside the decision.
          </caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Source</th>
              <th scope="col">Context</th>
              <th scope="col">Content</th>
              <th scope="col">Classification</th>
              <th scope="col">Type</th>
              <th scope="col">Model score</th>
              <th scope="col">Severity</th>
              <th scope="col">Review</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <ItemRow key={item.id} item={item} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
