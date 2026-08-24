import { isFallbackActive, isFixtureVisible } from '@/api';
import { useDataMode } from '@/app/DataModeProvider';

import styles from './FixtureBanner.module.css';

/**
 * Always-visible notice in fixture and fallback modes.
 *
 * The numbers on screen are synthetic. Hiding that would let a demo be
 * mistaken for a live reading.
 */
export function FixtureBanner() {
  const { mode } = useDataMode();
  const visible = isFixtureVisible(mode, isFallbackActive());

  if (!visible) {
    return null;
  }

  const label =
    mode === 'fallback' && isFallbackActive()
      ? 'Showing fixture data. The live service was unavailable.'
      : 'Showing fixture data. These figures are synthetic.';

  return <output className={styles.banner}>{label}</output>;
}
