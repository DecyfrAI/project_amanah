import { useEffect, useRef } from 'react';

import { useReducedMotion } from './useReducedMotion';

/**
 * Caps travel at this fraction of the measured parent's height. Without a cap,
 * a section near the bottom of a long page would be thrown off-frame.
 */
const OFFSET_LIMIT_RATIO = 0.2;

/**
 * Moves an element vertically against its parent's place in the viewport.
 *
 * Measures the parent, not the moving element, so the transform we write never
 * feeds back into the next reading. Writes the offset to a custom property
 * rather than to `style.transform`, so the stylesheet keeps ownership of how
 * that offset is used and the element can compose it with its own transforms.
 *
 * Updates are coalesced into one animation frame per scroll or resize burst,
 * and both listeners are passive so they never delay scrolling. Does nothing
 * at all when the reader prefers reduced motion.
 *
 * @param speed Fraction of the parent's displacement from the viewport centre
 * to travel. 0.3 reads as depth without inducing motion sickness.
 */
export function useParallax<T extends HTMLElement>(speed: number) {
  const elementRef = useRef<T>(null);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const element = elementRef.current;
    if (element === null || prefersReducedMotion) {
      return;
    }

    const measure = element.parentElement;
    if (measure === null) {
      return;
    }

    let frameId = 0;

    const applyOffset = (): void => {
      frameId = 0;
      const rect = measure.getBoundingClientRect();
      const displacement = rect.top + rect.height / 2 - window.innerHeight / 2;
      const raw = -displacement * speed;
      const limit = measure.clientHeight * OFFSET_LIMIT_RATIO;
      const offset = Math.max(-limit, Math.min(limit, raw));
      element.style.setProperty('--parallax-offset', `${offset}px`);
    };

    const scheduleOffset = (): void => {
      if (frameId === 0) {
        frameId = window.requestAnimationFrame(applyOffset);
      }
    };

    applyOffset();
    window.addEventListener('scroll', scheduleOffset, { passive: true });
    window.addEventListener('resize', scheduleOffset, { passive: true });

    return () => {
      window.removeEventListener('scroll', scheduleOffset);
      window.removeEventListener('resize', scheduleOffset);
      if (frameId !== 0) {
        window.cancelAnimationFrame(frameId);
      }
      element.style.removeProperty('--parallax-offset');
    };
  }, [speed, prefersReducedMotion]);

  return elementRef;
}
