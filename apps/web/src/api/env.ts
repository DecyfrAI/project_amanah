export const DATA_MODES = ['fixture', 'live', 'fallback'] as const;

export type DataMode = (typeof DATA_MODES)[number];

/**
 * Which source the running client reads from.
 *
 * Defaults to fixture so a missing env var never silently calls a live API
 * that is not there. Every VITE_ value is public; nothing sensitive belongs
 * here.
 */
export function readDataMode(): DataMode {
  const value = import.meta.env.VITE_DATA_MODE;
  if (value === 'live' || value === 'fallback' || value === 'fixture') {
    return value;
  }
  return 'fixture';
}

export function readApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
}

export function isFixtureVisible(mode: DataMode, fallbackActive: boolean): boolean {
  return mode === 'fixture' || (mode === 'fallback' && fallbackActive);
}
