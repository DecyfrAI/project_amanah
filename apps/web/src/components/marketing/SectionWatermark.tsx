import styles from './SectionWatermark.module.css';

/** أمانah, "a trust". Ornament only; never the sole carrier of meaning. */
const WORD = 'أمانة';
const REPEATS_PER_ROW = 6;

const ROW = Array.from({ length: REPEATS_PER_ROW }, (_, index) => index);

/**
 * Faint drifting Arabic ornament for light sections.
 *
 * Two identical rows sit in one track; the animation shifts by exactly half its
 * width, so the loop has no visible seam. Hidden from assistive technology and
 * inert to pointer events.
 */
export function SectionWatermark() {
  return (
    <div className={styles.watermark} aria-hidden="true">
      <div className={styles.track}>
        <div className={styles.row}>
          {ROW.map((index) => (
            <span key={`a-${index}`} className={styles.word} dir="rtl" lang="ar">
              {WORD}
            </span>
          ))}
        </div>
        <div className={styles.row}>
          {ROW.map((index) => (
            <span key={`b-${index}`} className={styles.word} dir="rtl" lang="ar">
              {WORD}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
