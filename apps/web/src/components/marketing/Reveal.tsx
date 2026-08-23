import type { CSSProperties, ReactNode } from 'react';

import { useScrollReveal } from '@/hooks/useScrollReveal';

import styles from './Reveal.module.css';

/**
 * Delay styles are shared across every Reveal that uses the same value, so a
 * fresh object is not handed to the element on every render.
 */
const delayStyles = new Map<number, CSSProperties>();

function delayStyle(delayMs: number): CSSProperties | undefined {
  if (delayMs <= 0) {
    return undefined;
  }
  const cached = delayStyles.get(delayMs);
  if (cached !== undefined) {
    return cached;
  }
  const style = { '--reveal-delay': `${delayMs}ms` } as CSSProperties;
  delayStyles.set(delayMs, style);
  return style;
}

interface RevealProps {
  children: ReactNode;
  /**
   * Milliseconds to hold before this element settles, for staggering a group.
   * Keep it small, a long delay reads as a bug rather than as choreography.
   */
  delayMs?: number;
  className?: string;
}

/**
 * Reveals its children once they scroll into view.
 *
 * Reveals a single time and then stops observing. Content that re-hides on
 * scroll-up is distracting, and reveals nothing to a reader who has already
 * read it. Inert under reduced motion, where children render immediately.
 */
export function Reveal({ children, delayMs = 0, className }: RevealProps) {
  const { elementRef, isRevealed } = useScrollReveal<HTMLDivElement>();

  return (
    <div
      ref={elementRef}
      style={delayStyle(delayMs)}
      className={[styles.reveal, isRevealed ? styles.revealed : '', className]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  );
}
