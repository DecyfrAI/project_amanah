import type { ReactNode } from 'react';

import styles from './DisplayHeading.module.css';

interface DisplayHeadingProps {
  /** Heading level. Levels must never be skipped within a page. */
  level: 1 | 2;
  /** Upright first line. */
  upright: string;
  /** Italic, accent-coloured second line. */
  accent: ReactNode;
  /** Hero headings step up one size at every breakpoint. */
  isHero?: boolean;
  /**
   * Stable name announced instead of the visible text.
   *
   * Required when `accent` changes over time: a heading whose text mutates
   * every few seconds is unusable with a screen reader, so the visible content
   * is hidden from assistive technology and this is announced in its place.
   */
  accessibleName?: string;
}

/**
 * Two-line editorial heading: an upright line above a coloured italic line.
 *
 * When the name is stable, both lines sit in one heading element so assistive
 * technology announces a single continuous phrase.
 */
export function DisplayHeading({
  level,
  upright,
  accent,
  isHero = false,
  accessibleName,
}: DisplayHeadingProps) {
  const Tag = level === 1 ? 'h1' : 'h2';
  const className = isHero ? `${styles.heading} ${styles.hero}` : styles.heading;

  const lines = (
    <>
      <span className={styles.upright}>{upright}</span>{' '}
      <span className={styles.accent}>{accent}</span>
    </>
  );

  if (accessibleName === undefined) {
    return <Tag className={className}>{lines}</Tag>;
  }

  return (
    <Tag className={className}>
      <span className="visually-hidden">{accessibleName}</span>
      <span aria-hidden="true">{lines}</span>
    </Tag>
  );
}
