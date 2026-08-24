import { readDataMode, type DataMode } from './env';

const MOCK_DATA_STORAGE_KEY = 'amanah.use-mock-data';

/**
 * The request source selected by the viewer.
 *
 * Only the fixture override is stored. Removing it restores the mode chosen by
 * the build, so a browser preference can never silently select a different
 * live environment.
 */
export function readSelectedDataMode(): DataMode {
  try {
    if (localStorage.getItem(MOCK_DATA_STORAGE_KEY) === '1') {
      return 'fixture';
    }
  } catch {
    // Storage can be unavailable in privacy modes; the build mode still works.
  }

  return readDataMode();
}

export function writeMockDataPreference(isEnabled: boolean): void {
  try {
    if (isEnabled) {
      localStorage.setItem(MOCK_DATA_STORAGE_KEY, '1');
      return;
    }
    localStorage.removeItem(MOCK_DATA_STORAGE_KEY);
  } catch {
    // The in-memory selection still applies for this visit.
  }
}

export function clearMockDataPreference(): void {
  try {
    localStorage.removeItem(MOCK_DATA_STORAGE_KEY);
  } catch {
    // There is no stored preference to clear when storage is unavailable.
  }
}
