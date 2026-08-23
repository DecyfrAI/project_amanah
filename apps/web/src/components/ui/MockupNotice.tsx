import styles from './MockupNotice.module.css';

interface MockupNoticeProps {
  /** What a reader of this particular page might otherwise take the figures for. */
  detail: string;
  /** Closing sentence. Override when this page also has a live flow. */
  controlsNote?: string;
}

/**
 * States, above everything else on the page, that the figures were written not read.
 *
 * Several workspace views exist as design mockups built from local constants so
 * the layout could be reviewed before the API exists. An illustration a reader
 * cannot tell from a reading is the one thing this product must not ship, so the
 * statement belongs in the page rather than in a caption under it.
 */
export function MockupNotice({
  detail,
  controlsNote = 'Nothing here was collected, and no control on this page reads or writes anything.',
}: MockupNoticeProps) {
  return (
    <aside className={styles.notice} aria-labelledby="mockup-notice-label">
      <p className={styles.label}>
        <span className={styles.icon} aria-hidden="true">
          <DraftIcon />
        </span>
        <strong id="mockup-notice-label">Design mockup, not a reading</strong>
      </p>
      <p className={styles.body}>
        Every figure, row, and timestamp on this page is a local constant written to show the
        layout. {detail} {controlsNote}
      </p>
    </aside>
  );
}

function DraftIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M4 19.5V17l9.5-9.5 2.5 2.5L6.5 19.5Z" />
      <path d="M15 5.5 17 3.5l3.5 3.5-2 2Z" />
      <path d="M4 21.5h16" />
    </svg>
  );
}
