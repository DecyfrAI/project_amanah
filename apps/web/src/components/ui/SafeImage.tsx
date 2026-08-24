import { useCallback, useId, useState } from 'react';

import { useMediaPreference } from '@/features/settings/media-preference';

import styles from './SafeImage.module.css';

interface SafeImageProps {
  readonly src: string;
  /** Describes the form of the image, never its slogans. Required. */
  readonly alt: string;
  /** Optional line shown under the control, e.g. file metadata. */
  readonly note?: string;
  /** Verb pair for the control, e.g. `image` gives "Hide image"/"Show image". */
  readonly subject?: string;
  readonly className?: string;
}

/**
 * One research image, shown under the viewer's own display preference (PA-01).
 *
 * Visible by default. When the viewer has opted in to blurring, the image
 * renders blurred and the control offers to show it. Either way the control is
 * a real button with an accessible name, so one image can be overridden without
 * changing the global preference — and a preference change reaches an
 * already-rendered image immediately, because the blur is derived on render
 * rather than copied into state.
 *
 * The image is always fetched through the same authenticated path. Blur is a
 * display treatment and never an access control.
 */
export function SafeImage({ src, alt, note, subject = 'image', className }: SafeImageProps) {
  const { blurMedia } = useMediaPreference();
  const [override, setOverride] = useState<boolean | null>(null);
  const imageId = useId();

  // `null` means "follow the global preference". A per-image choice wins until
  // the viewer clears it by toggling back.
  const isBlurred = override ?? blurMedia;

  const handleToggle = useCallback((): void => {
    setOverride(!isBlurred);
  }, [isBlurred]);

  const imageClass = isBlurred ? `${styles.image} ${styles.imageBlurred}` : styles.image;

  return (
    <figure className={className === undefined ? styles.figure : `${styles.figure} ${className}`}>
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={!isBlurred}
        aria-controls={imageId}
        onClick={handleToggle}
      >
        {isBlurred ? `Show ${subject}` : `Hide ${subject}`}
      </button>
      <img id={imageId} className={imageClass} src={src} alt={alt} loading="lazy" />
      {note !== undefined && <figcaption className={styles.note}>{note}</figcaption>}
    </figure>
  );
}
