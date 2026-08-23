import { useCallback, useState } from 'react';

import styles from './EvidencePreview.module.css';

interface EvidencePreviewProps {
  readonly src: string;
  readonly filename: string;
}

/**
 * Screenshot stays in this tab as an object URL. It is blurred until the
 * reader asks to see it. Quoted words in the email are not redacted.
 */
export function EvidencePreview({ src, filename }: EvidencePreviewProps) {
  const [isRevealed, setIsRevealed] = useState(false);

  const toggle = useCallback((): void => {
    setIsRevealed((current) => !current);
  }, []);

  return (
    <figure className={styles.figure}>
      <p className={styles.warning}>
        Harmful media stays blurred until you reveal it. The file has not left this tab.
      </p>
      <button
        type="button"
        className={styles.reveal}
        onClick={toggle}
        aria-expanded={isRevealed}
        aria-controls="evidence-preview-image"
      >
        {isRevealed ? 'Hide screenshot' : 'Reveal screenshot'}
      </button>
      <img
        id="evidence-preview-image"
        className={isRevealed ? styles.image : `${styles.image} ${styles.imageBlurred}`}
        src={src}
        alt={`Screenshot ${filename}, still on this device.`}
      />
    </figure>
  );
}
