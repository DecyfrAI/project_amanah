import { useCallback, useState } from 'react';

import styles from './FlipCard.module.css';

interface FlipCardProps {
  /** Short label in monospace above the summary. */
  name: string;
  /** The claim, shown on the front. */
  summary: string;
  /** The substantiation, shown on the back. */
  detail: string;
}

/**
 * Card that turns over to reveal its detail.
 *
 * The whole card is one button with `aria-pressed`, so it is keyboard operable
 * and announced without invented ARIA.
 *
 * A button collapses its contents into a single node for assistive technology,
 * so the visible text alone would leave the detail unannounced. The accessible
 * name therefore tracks the flip state and carries whichever face is showing ,
 * a screen-reader user gets exactly what a sighted user gets, in the same order.
 */
export function FlipCard({ name, summary, detail }: FlipCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  const toggle = useCallback((): void => {
    setIsFlipped((current) => !current);
  }, []);

  const accessibleName = isFlipped
    ? `${name}. ${detail} Press to show the summary again.`
    : `${name}. ${summary} Press to show how we hold to it.`;

  return (
    <button
      type="button"
      className={`${styles.card} ${isFlipped ? styles.flipped : ''}`}
      aria-pressed={isFlipped}
      aria-label={accessibleName}
      onClick={toggle}
    >
      <span className={styles.inner}>
        <span className={`${styles.face} ${styles.front}`}>
          <span className={styles.name}>{name}</span>
          <span className={styles.summary}>{summary}</span>
          <span className={styles.hint}>
            How we hold to it
            <ArrowIcon />
          </span>
        </span>

        <span className={`${styles.face} ${styles.back}`}>
          <span className={styles.name}>{name}</span>
          <span className={styles.detail}>{detail}</span>
          <span className={styles.hint}>
            Back
            <ArrowIcon />
          </span>
        </span>
      </span>
    </button>
  );
}

function ArrowIcon() {
  return (
    <svg
      className={styles.hintIcon}
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      aria-hidden="true"
    >
      <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
