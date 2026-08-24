import { useEffect, useState } from 'react';

import { useTheme } from '@/app/ThemeProvider';
import { Logo } from '@/brand/Logo';

import { ENTRY_HEADLINES, ENTRY_TIPS } from './entry-copy';

import styles from './AppLoadingScreen.module.css';

interface AppLoadingScreenProps {
  /** Spoken and visible status. Defaults to a generic route-chunk wait. */
  message?: string;
  /**
   * Post-login hold: larger lockup, rotating headline, and one rotating tip.
   * The Suspense fallback stays a short wait without those extras.
   */
  hold?: boolean;
}

/** How often the headline and tip change. Keep in step with `--duration-tip-cycle`. */
export const TIP_CYCLE_MS = 3000;

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Branded hold: a large logo, a large wheel, and a line of copy.
 *
 * After sign-in the headline and a single tip rotate. Motion stops under
 * reduced motion.
 */
export function AppLoadingScreen({
  message = 'Opening Project Amanah',
  hold = false,
}: AppLoadingScreenProps) {
  const { theme } = useTheme();

  return (
    <output className={styles.screen} aria-live="polite" aria-busy="true">
      <Logo variant={theme === 'dark' ? 'inverse' : 'default'} size={hold ? 'splash' : 'large'} />
      <span className={hold ? styles.wheelLarge : styles.wheel} aria-hidden="true" />
      {hold ? <EntryCopy /> : <span className={styles.label}>{message}</span>}
    </output>
  );
}

function EntryCopy() {
  const [headlineIndex, setHeadlineIndex] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion()) {
      return;
    }
    const timer = window.setInterval(() => {
      setHeadlineIndex((current) => (current + 1) % ENTRY_HEADLINES.length);
      setTipIndex((current) => (current + 1) % ENTRY_TIPS.length);
    }, TIP_CYCLE_MS);
    return () => {
      window.clearInterval(timer);
    };
  }, []);

  const tip = ENTRY_TIPS[tipIndex] ?? ENTRY_TIPS[0];

  return (
    <div className={styles.entryCopy}>
      <p className={styles.headline}>{ENTRY_HEADLINES[headlineIndex]}</p>
      <p key={tip} className={styles.tip}>
        {tip}
      </p>
    </div>
  );
}
