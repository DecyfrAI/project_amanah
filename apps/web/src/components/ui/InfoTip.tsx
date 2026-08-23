import type { ReactNode } from 'react';

import styles from './InfoTip.module.css';

interface InfoTipProps {
  /** Short name of the figure, used in the accessible label. */
  label: string;
  /**
   * `card` lines the glyph up with a boxed title: same row, and the same
   * inset from the trailing edge as the title has from the leading edge. The
   * hit target stays the minimum size; it overflows the glyph.
   */
  placement?: 'inline' | 'card';
  children: ReactNode;
}

/**
 * A small circled question mark that reveals a definition on hover or focus.
 *
 * Colour is never the only cue: the panel carries the words. The trigger keeps
 * a visible focus ring from the global focus styles.
 */
export function InfoTip({ label, placement = 'inline', children }: InfoTipProps) {
  const tipId = `info-tip-${label.replace(/\s+/g, '-').toLowerCase()}`;
  const wrapClass = placement === 'card' ? `${styles.wrap} ${styles.wrapCard}` : styles.wrap;

  return (
    <span className={wrapClass}>
      <button
        type="button"
        className={styles.trigger}
        aria-label={`About ${label}`}
        aria-describedby={tipId}
      >
        <span className={styles.glyph} aria-hidden="true">
          <QuestionMarkIcon />
        </span>
      </button>
      <span id={tipId} role="tooltip" className={styles.panel}>
        {children}
      </span>
    </span>
  );
}

function QuestionMarkIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={24}
      height={24}
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.6 9.4a2.4 2.4 0 1 1 3.5 2.15c-.85.45-1.2 1-1.2 1.95" />
      <circle cx="12" cy="16.6" r="0.85" fill="currentColor" stroke="none" />
    </svg>
  );
}
