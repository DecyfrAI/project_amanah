import { useEffect, useState } from 'react';

import { useReducedMotion } from './useReducedMotion';

/** How long each phrase is held before the next one replaces it. */
const PHRASE_DURATION_MS = 2800;

interface RotatingPhrase {
  /** The phrase currently shown. */
  phrase: string;
  /** Index of the current phrase, for keying the enter animation. */
  index: number;
}

/**
 * Cycles through a list of phrases on a fixed interval.
 *
 * Holds on the first phrase when the reader prefers reduced motion, so the
 * headline is simply static rather than animated. Callers are responsible for
 * hiding the rotating element from assistive technology and supplying a stable
 * accessible name; a heading whose text changes every few seconds is hostile
 * to screen readers.
 */
export function useRotatingPhrase(phrases: readonly string[]): RotatingPhrase {
  const prefersReducedMotion = useReducedMotion();
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion || phrases.length <= 1) {
      return;
    }

    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % phrases.length);
    }, PHRASE_DURATION_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [prefersReducedMotion, phrases.length]);

  return { phrase: phrases[index] ?? '', index };
}
