import { SafeImage } from '@/components/ui/SafeImage';

import styles from './EvidencePreview.module.css';

interface EvidencePreviewProps {
  readonly src: string;
  readonly filename: string;
}

/**
 * Screenshot stays in this tab as an object URL. It follows the viewer's own
 * display preference (PA-01) and keeps a per-image Show/Hide control. Quoted
 * words in the draft are not redacted.
 */
export function EvidencePreview({ src, filename }: EvidencePreviewProps) {
  return (
    <div className={styles.figure}>
      <p className={styles.warning}>The file has not left this tab.</p>
      <SafeImage
        src={src}
        alt={`Screenshot ${filename}, still on this device.`}
        subject="screenshot"
      />
    </div>
  );
}
