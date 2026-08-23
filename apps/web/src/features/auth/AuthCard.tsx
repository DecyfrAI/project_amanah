import type { ReactNode } from 'react';

import { useTheme } from '@/app/ThemeProvider';
import { Logo } from '@/brand/Logo';

import { AuthArabicOverlay } from './AuthArabicOverlay';

import styles from './AuthCard.module.css';

interface AuthCardProps {
  /** Page heading. One `h1` per view. */
  heading: string;
  /** What this screen actually does, stated before the fields. */
  intro: ReactNode;
  children: ReactNode;
  /** Route to the other auth screen. */
  footer: ReactNode;
}

/**
 * Shared frame for the login and sign-up screens.
 *
 * Both are a single narrow column: a form this short does not benefit from a
 * split hero layout, and a centred column reflows to one hand on a phone
 * without a second breakpoint.
 */
export function AuthCard({ heading, intro, children, footer }: AuthCardProps) {
  const { theme } = useTheme();

  return (
    // Carries the skip-link target, since these routes sit outside the
    // marketing layout that normally provides it.
    <main id="main" className={styles.page}>
      <AuthArabicOverlay />
      <section className={styles.card} aria-labelledby="auth-heading">
        <div className={styles.brand}>
          <Logo variant={theme === 'dark' ? 'inverse' : 'default'} lockup="stacked" size="auth" />
        </div>
        <h1 id="auth-heading" className={styles.heading}>
          {heading}
        </h1>
        <div className={styles.intro}>{intro}</div>
        {children}
        <p className={styles.footer}>{footer}</p>
      </section>
    </main>
  );
}
