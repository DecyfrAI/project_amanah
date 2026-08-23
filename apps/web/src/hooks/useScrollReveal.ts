import { useEffect, useRef, useState } from 'react';

import { useReducedMotion } from './useReducedMotion';

/** Reveal once the element is this far into the viewport. */
const REVEAL_THRESHOLD = 0.15;

/**
 * Reports whether an element has scrolled into view.
 *
 * Reveals once and then stops observing: content that re-hides on scroll-up is
 * distracting and makes the page feel unstable. Always reports revealed when
 * the reader prefers reduced motion, so nothing is ever hidden behind an
 * animation that will not play.
 */
export function useScrollReveal<T extends HTMLElement>() {
  const elementRef = useRef<T>(null);
  const prefersReducedMotion = useReducedMotion();
  const [hasIntersected, setHasIntersected] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (element === null || prefersReducedMotion) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting === true) {
          setHasIntersected(true);
          observer.disconnect();
        }
      },
      { threshold: REVEAL_THRESHOLD },
    );

    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, [prefersReducedMotion]);

  // Derived rather than written from the effect, so a preference change takes
  // effect on the next render without a second state write.
  return { elementRef, isRevealed: prefersReducedMotion || hasIntersected };
}
