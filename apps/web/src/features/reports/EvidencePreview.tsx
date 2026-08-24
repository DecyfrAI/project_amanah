import { SafeImage } from '@/components/ui/SafeImage';

import styles from './EvidencePreview.module.css';

interface EvidencePreviewProps {
  readonly src: string;
  readonly filename: string;
}

/**
 * The preview is a tab-local object URL even when another part of the flow also
 * uploads a cleaned copy. It follows the viewer's own display preference
 * (PA-01) and keeps a per-image Show/Hide control.
 */
export function EvidencePreview({ src, filename }: EvidencePreviewProps) {
  return (
    <div className={styles.figure}>
      <p className={styles.warning}>Local preview of the file you selected.</p>
      <SafeImage src={src} alt={`Preview of ${filename}.`} subject="screenshot" />
    </div>
  );
}
