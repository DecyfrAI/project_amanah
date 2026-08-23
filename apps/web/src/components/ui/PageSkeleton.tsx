import styles from './PageSkeleton.module.css';

interface PageSkeletonProps {
  /**
   * Describes what is loading, for the screen-reader announcement. Should name
   * the destination, "Overview", "Explorer", not just say "content".
   */
  label: string;
}

/**
 * Suspense fallback for a route-level code split.
 *
 * Announces politely rather than assertively so it does not interrupt a reader
 * mid-sentence. `<output>` carries an implicit ARIA status role, so the wait is
 * perceivable without sight. rules/frontend.md requires every loading indicator
 * to carry an accessible description.
 */
export function PageSkeleton({ label }: PageSkeletonProps) {
  return (
    <output className={styles.container} aria-live="polite" aria-busy="true">
      <span className="visually-hidden">Loading {label}</span>
      <div className={`${styles.bar} ${styles.barTitle}`} />
      <div className={`${styles.bar} ${styles.barWide}`} />
      <div className={`${styles.bar} ${styles.barMedium}`} />
      <div className={`${styles.bar} ${styles.barNarrow}`} />
    </output>
  );
}
