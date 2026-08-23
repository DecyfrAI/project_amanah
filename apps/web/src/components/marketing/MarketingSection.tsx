import type { ReactNode } from 'react';

import { SectionWatermark } from './SectionWatermark';

import styles from './MarketingSection.module.css';

interface MarketingSectionProps {
  /** Which ground this section sits on. Sections alternate down the page. */
  tone: 'dark' | 'light';
  /** Anchor target for in-page navigation. */
  id?: string;
  /** Labels the section for assistive technology, naming its heading. */
  ariaLabelledBy?: string;
  /**
   * Draws the drifting أمانة ornament behind the content. Used on every
   * content section. The hero and the footer stay clear of it.
   */
  hasWatermark?: boolean;
  children: ReactNode;
}

/**
 * A full-width marketing section on either a dark or a light ground.
 *
 * Sets the --marketing-* custom properties its children read, so the
 * primitives inside stay ignorant of which ground they are on.
 */
export function MarketingSection({
  tone,
  id,
  ariaLabelledBy,
  hasWatermark = false,
  children,
}: MarketingSectionProps) {
  return (
    <section
      id={id}
      aria-labelledby={ariaLabelledBy}
      className={`${styles.section} ${styles[tone]}`}
    >
      {hasWatermark && <SectionWatermark />}
      <div className={styles.inner}>{children}</div>
    </section>
  );
}
