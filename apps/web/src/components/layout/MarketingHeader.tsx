import { useCallback, useEffect, useRef, useState } from 'react';

import { Logo } from '@/brand/Logo';
import { ButtonLink } from '@/components/ui/Button';

import { MARKETING_SECTIONS } from './marketing-sections';

import styles from './MarketingHeader.module.css';

/** Distance scrolled before the bar takes on its own background. */
const SCROLLED_THRESHOLD_PX = 24;

export function MarketingHeader() {
  const [isScrolled, setIsScrolled] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const menuToggleRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleScroll = (): void => {
      setIsScrolled(window.scrollY > SCROLLED_THRESHOLD_PX);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // A native modal dialog supplies the focus trap, the Escape handler, and
  // inert background content, all of which rules/frontend.md requires and all
  // of which are easy to get subtly wrong by hand.
  const openDrawer = useCallback((): void => {
    dialogRef.current?.showModal();
  }, []);

  const closeDrawer = useCallback((): void => {
    dialogRef.current?.close();
  }, []);

  // Runs however the dialog was dismissed, including via Escape, so focus
  // always returns to the control that opened it.
  const restoreFocus = useCallback((): void => {
    menuToggleRef.current?.focus();
  }, []);

  return (
    <>
      <header className={`${styles.header} ${isScrolled ? styles.scrolled : ''}`}>
        <div className={styles.inner}>
          <Logo variant="inverse" size="header" />

          <nav className={styles.nav} aria-label="Page sections">
            <ul className={styles.navList}>
              {MARKETING_SECTIONS.map((section) => (
                <li key={section.href}>
                  <a className={styles.navLink} href={section.href}>
                    {section.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <div className={styles.actions}>
            {/*
              Marketing is the only anonymous surface, so it leads with
              accounts. Sign up is the primary action; Log in sits beside it.
              See ADR 0001 and spec.md FR-HOME-002.
            */}
            <span className={styles.desktopActions}>
              <ButtonLink variant="secondary" to="/login">
                Log in
              </ButtonLink>
              <ButtonLink variant="primary" to="/signup">
                Sign up
              </ButtonLink>
            </span>
            <button
              ref={menuToggleRef}
              type="button"
              className={styles.menuToggle}
              aria-label="Open menu"
              onClick={openDrawer}
            >
              <MenuIcon />
            </button>
          </div>
        </div>
      </header>

      <dialog
        ref={dialogRef}
        className={styles.drawer}
        aria-label="Page sections"
        onClose={restoreFocus}
      >
        <div className={styles.drawerHeader}>
          <Logo variant="inverse" size="medium" />
          <button
            type="button"
            className={styles.menuToggle}
            aria-label="Close menu"
            onClick={closeDrawer}
          >
            <CloseIcon />
          </button>
        </div>

        <nav aria-label="Page sections">
          <ul className={styles.drawerList}>
            {MARKETING_SECTIONS.map((section) => (
              <li key={section.href}>
                <a className={styles.drawerLink} href={section.href} onClick={closeDrawer}>
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.drawerActions}>
          <ButtonLink variant="secondary" to="/login">
            Log in
          </ButtonLink>
          <ButtonLink variant="primary" to="/signup">
            Sign up
          </ButtonLink>
        </div>
      </dialog>
    </>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3 6h14M3 10h14M3 14h14" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
