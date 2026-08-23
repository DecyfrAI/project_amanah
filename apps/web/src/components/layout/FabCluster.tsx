import type { ReactNode } from 'react';

import { requestWorkspaceTour } from '@/features/tour/tour-storage';

import styles from './FabCluster.module.css';

interface FabClusterProps {
  ask: ReactNode;
}

/**
 * Fixed bottom-right controls for the authenticated workspace.
 *
 * Tour sits above Ask so the primary Ask bubble stays the larger, lower control.
 */
export function FabCluster({ ask }: FabClusterProps) {
  return (
    <div className={styles.cluster}>
      <button
        type="button"
        className={styles.help}
        onClick={requestWorkspaceTour}
        aria-label="Tour"
        title="How to use this workspace"
      >
        <span className={styles.helpGlyph} aria-hidden="true">
          ?
        </span>
      </button>
      {ask}
    </div>
  );
}
