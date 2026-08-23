import { Link } from 'react-router-dom';

import styles from './Logo.module.css';

interface LogoProps {
  /** `inverse` is the light-on-dark lockup, for navy grounds. */
  variant: 'default' | 'inverse';
  size?: 'small' | 'medium' | 'large' | 'header' | 'sidebar' | 'splash' | 'auth';
  /**
   * Which generated lockup to use. `stacked` puts the symbol above the wordmark
   * for a narrow column, `mark` drops the wordmark entirely for a collapsed rail.
   * The accessible name never changes, since it is the same brand either way.
   */
  lockup?: 'wordmark' | 'stacked' | 'mark';
}

/** Intrinsic dimensions of each generated asset, used to reserve space. */
const WORDMARK_WIDTH = 720;
const WORDMARK_HEIGHT = 256;
const STACKED_WIDTH = 512;
const STACKED_HEIGHT = 318;
const MARK_SIZE = 256;

/**
 * The Project Amanah wordmark, linking home.
 *
 * Width and height are declared so the header does not shift while the image
 * loads. The alt text names the brand, satisfying the brand system's
 * requirement that the logo carry meaningful accessible text.
 */
const ASSETS = {
  wordmark: { family: 'amanah-wordmark', width: WORDMARK_WIDTH, height: WORDMARK_HEIGHT },
  stacked: { family: 'amanah-stacked', width: STACKED_WIDTH, height: STACKED_HEIGHT },
  mark: { family: 'amanah-mark', width: MARK_SIZE, height: MARK_SIZE },
} as const;

export function Logo({ variant, size = 'medium', lockup = 'wordmark' }: LogoProps) {
  const asset = ASSETS[lockup];
  const source = variant === 'inverse' ? `${asset.family}-inverse` : asset.family;
  // The stacked and square lockups are sized by their own rule rather than by the
  // horizontal size scale, which is calibrated to a single line of wordmark.
  const sizeClass =
    lockup === 'stacked' && size === 'auth'
      ? styles.stackedAuth
      : lockup === 'wordmark'
        ? styles[size]
        : styles[lockup];

  return (
    <Link className={styles.logo} to="/">
      <img
        className={`${styles.image} ${sizeClass}`}
        src={`/brand/${source}.png`}
        width={asset.width}
        height={asset.height}
        alt="Project Amanah"
      />
    </Link>
  );
}
