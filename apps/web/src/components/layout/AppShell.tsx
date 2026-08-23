import { Suspense, useCallback, useRef, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';

import { useTheme } from '@/app/ThemeProvider';
import { Logo } from '@/brand/Logo';
import { FabCluster } from '@/components/layout/FabCluster';
import { Avatar } from '@/components/ui/Avatar';
import { FixtureBanner } from '@/components/ui/FixtureBanner';
import { PageSkeleton } from '@/components/ui/PageSkeleton';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { AskAmanah } from '@/features/ask/AskAmanah';
import { endFixtureSession, readFixtureSession } from '@/features/auth/session';
import { WorkspaceTour } from '@/features/tour/WorkspaceTour';

import { WorkspaceNav } from './WorkspaceNav';

import styles from './AppShell.module.css';

const COLLAPSE_KEY = 'amanah.sidebar-collapsed';

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1';
  } catch {
    return false;
  }
}

/**
 * Chrome for every authenticated route.
 *
 * The sidebar persists across tab changes and the Suspense boundary sits inside
 * it, so switching tabs replaces the panel instead of blanking the page and
 * losing the reader's place.
 */
export function AppShell() {
  const navigate = useNavigate();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const menuToggleRef = useRef<HTMLButtonElement>(null);
  const [isCollapsed, setIsCollapsed] = useState<boolean>(readCollapsed);
  const session = readFixtureSession();
  const displayName = session?.displayName ?? 'Demo reviewer';
  const { theme } = useTheme();
  const logoVariant = theme === 'dark' ? 'inverse' : 'default';

  const handleLogout = useCallback((): void => {
    endFixtureSession();
    void navigate('/');
  }, [navigate]);

  const toggleCollapsed = useCallback((): void => {
    setIsCollapsed((current) => {
      const next = !current;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
      } catch {
        // A preference that cannot be remembered still applies for this visit.
      }
      return next;
    });
  }, []);

  // A native dialog brings the focus trap, Escape handling, and inert
  // background that a hand-rolled drawer usually gets wrong.
  const openDrawer = useCallback((): void => {
    dialogRef.current?.showModal();
  }, []);

  const closeDrawer = useCallback((): void => {
    dialogRef.current?.close();
  }, []);

  const restoreFocus = useCallback((): void => {
    menuToggleRef.current?.focus();
  }, []);

  return (
    <div className={styles.shell}>
      <FixtureBanner />

      <div className={styles.body}>
        <aside
          className={isCollapsed ? `${styles.sidebar} ${styles.sidebarNarrow}` : styles.sidebar}
        >
          <div className={styles.brand}>
            <Logo variant={logoVariant} size="sidebar" lockup={isCollapsed ? 'mark' : 'stacked'} />
          </div>

          {/*
           * Only the tab list scrolls. The brand above it and the identity block
           * below it are pinned, so nothing shifts position as tabs are added or
           * the viewport shortens.
           */}
          <nav className={styles.tabs} aria-label="Workspace">
            <WorkspaceNav isCollapsed={isCollapsed} />
          </nav>

          <div className={styles.sidebarFooter}>
            <Link className={styles.profileLink} to="/app/profile">
              <Avatar displayName={displayName} imageSrc={session?.avatarDataUrl ?? null} />
              <span className={isCollapsed ? 'visually-hidden' : styles.profileText}>
                <span className={styles.profileName}>{displayName}</span>
                <span className={styles.profileHint}>Profile and account</span>
              </span>
            </Link>

            <ThemeToggle isCompact={isCollapsed} />

            <button
              type="button"
              className={styles.collapseToggle}
              onClick={toggleCollapsed}
              aria-expanded={!isCollapsed}
            >
              <span className={styles.collapseIcon} aria-hidden="true">
                {isCollapsed ? <ExpandIcon /> : <CollapseIcon />}
              </span>
              <span className={isCollapsed ? 'visually-hidden' : undefined}>
                {isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              </span>
            </button>
          </div>
        </aside>

        <div className={styles.content}>
          <WorkspaceTour />
          <header className={styles.topbar}>
            <button
              ref={menuToggleRef}
              type="button"
              className={styles.menuToggle}
              onClick={openDrawer}
            >
              Menu
            </button>

            <Link className={styles.viewer} to="/app/profile">
              <span className={styles.viewerText}>
                <span className={styles.viewerLabel}>Signed in as</span>
                <span className={styles.viewerName}>{displayName}</span>
              </span>
              <Avatar
                displayName={displayName}
                imageSrc={session?.avatarDataUrl ?? null}
                size="small"
              />
            </Link>

            <button type="button" className={styles.logout} onClick={handleLogout}>
              Log out
            </button>
          </header>

          <main id="main" className={styles.main}>
            <Suspense fallback={<PageSkeleton label="this view" />}>
              <Outlet />
            </Suspense>
          </main>
        </div>
      </div>

      <FabCluster ask={<AskAmanah />} />

      <dialog
        ref={dialogRef}
        className={styles.drawer}
        aria-label="Workspace"
        onClose={restoreFocus}
      >
        <div className={styles.drawerHeader}>
          <Logo variant={logoVariant} size="small" />
          <button type="button" className={styles.menuToggle} onClick={closeDrawer}>
            Close
          </button>
        </div>
        <nav aria-label="Workspace sections">
          <WorkspaceNav onNavigate={closeDrawer} />
        </nav>
        <Link className={styles.profileLink} to="/app/profile" onClick={closeDrawer}>
          <Avatar displayName={displayName} imageSrc={session?.avatarDataUrl ?? null} />
          <span className={styles.profileText}>
            <span className={styles.profileName}>{displayName}</span>
            <span className={styles.profileHint}>Profile and account</span>
          </span>
        </Link>
        <ThemeToggle />
      </dialog>
    </div>
  );
}

function CollapseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={24}
      height={24}
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M14 6 8 12l6 6" />
    </svg>
  );
}

function ExpandIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={24}
      height={24}
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M10 6l6 6-6 6" />
    </svg>
  );
}
