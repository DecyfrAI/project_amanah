import styles from './EyebrowPill.module.css';

interface EyebrowPillProps {
  children: string;
}

/** Small bordered pill with a status dot, sitting above a display heading. */
export function EyebrowPill({ children }: EyebrowPillProps) {
  return (
    <p className={styles.pill}>
      <span className={styles.dot} aria-hidden="true" />
      {children}
    </p>
  );
}
