import styles from './SectionLabel.module.css';

interface SectionLabelProps {
  /** Two-digit section number, e.g. "01". Omitted on sections that are not numbered. */
  ordinal?: string;
  children: string;
}

/**
 * Monospace uppercase section marker, optionally numbered.
 *
 * Rendered as a plain element rather than a heading so it never competes with
 * the real heading level and never introduces a skipped level.
 */
export function SectionLabel({ ordinal, children }: SectionLabelProps) {
  return (
    <p className={styles.label}>
      {ordinal !== undefined && (
        <>
          <span className={styles.ordinal}>{ordinal}</span>
          <span className={styles.rule} aria-hidden="true" />
        </>
      )}
      <span>{children}</span>
    </p>
  );
}
