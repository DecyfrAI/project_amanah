import { useState, type MouseEvent } from 'react';

import { useDataMode } from '@/app/DataModeProvider';

import styles from './DataModeToggle.module.css';

/** Switches product requests between the configured service and fixtures. */
export function DataModeToggle() {
  const { canUseLiveData, isMockDataEnabled, setMockDataEnabled } = useDataMode();
  const [isSwitching, setIsSwitching] = useState(false);
  const isDisabled = isSwitching || (!canUseLiveData && isMockDataEnabled);
  const title = !canUseLiveData
    ? 'This build is configured to use mock data.'
    : isMockDataEnabled
      ? 'Switch to live data'
      : 'Switch to mock data';

  // A native button does not benefit from a stable callback reference.
  // oxlint-disable-next-line react-perf/jsx-no-new-function-as-prop
  const handleToggle = async (event: MouseEvent<HTMLButtonElement>): Promise<void> => {
    const isEnabled = event.currentTarget.getAttribute('aria-checked') === 'true';
    setIsSwitching(true);
    try {
      await setMockDataEnabled(!isEnabled);
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <button
      type="button"
      role="switch"
      aria-label="Mock data"
      aria-checked={isMockDataEnabled}
      className={styles.toggle}
      disabled={isDisabled}
      title={title}
      onClick={handleToggle}
    >
      <span className={styles.label}>Mock data</span>
      <span
        className={isMockDataEnabled ? `${styles.track} ${styles.trackEnabled}` : styles.track}
        aria-hidden="true"
      >
        <span className={styles.thumb} />
      </span>
    </button>
  );
}
