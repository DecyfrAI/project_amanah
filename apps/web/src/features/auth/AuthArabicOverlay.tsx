import styles from './AuthArabicOverlay.module.css';

/** أمانة, "a trust". Ornament only; never the sole carrier of meaning. */
const WORD = 'أمانة';
const REPEATS_PER_ROW = 8;
const ROW_COUNT = 6;

const CELLS = Array.from({ length: REPEATS_PER_ROW }, (_, index) => index);
const ROWS = Array.from({ length: ROW_COUNT }, (_, index) => index);

/**
 * Repeating Arabic watermark behind the login and sign-up cards.
 *
 * Every row travels in the same direction. Two identical copies sit in one
 * track so a shift of exactly half the width loops without a seam. Hidden from
 * assistive technology and inert.
 */
export function AuthArabicOverlay() {
  return (
    <div className={styles.overlay} aria-hidden="true">
      {ROWS.map((row) => (
        <div key={row} className={styles.track}>
          <WordRow prefix={`${String(row)}-a`} />
          <WordRow prefix={`${String(row)}-b`} />
        </div>
      ))}
    </div>
  );
}

function WordRow({ prefix }: { prefix: string }) {
  return (
    <div className={styles.row}>
      {CELLS.map((index) => (
        <span key={`${prefix}-${String(index)}`} className={styles.word} dir="rtl" lang="ar">
          {WORD}
        </span>
      ))}
    </div>
  );
}
