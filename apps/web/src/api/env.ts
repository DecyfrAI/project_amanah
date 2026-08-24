export const DATA_MODES = ['fixture', 'live', 'fallback', 'demo'] as const;

export type DataMode = (typeof DATA_MODES)[number];

/**
 * Which source the running client reads from.
 *
 * - `fixture`: everything comes from committed synthetic data.
 * - `live`: every request goes to the deployed API; a failure stays a failure.
 * - `demo`: the hackathon hybrid. Product data (news, dashboard, items,
 *   assistant, insights, reports, images) is live and authenticated; the
 *   surfaces that remain mocked are labelled in place and never substitute for
 *   a failed live call.
 * - `fallback`: legacy try-live-then-fixture with a visible banner.
 *
 * Defaults to fixture so a missing env var never silently calls a live API
 * that is not there. Every VITE_ value is public; nothing sensitive belongs
 * here.
 */
export function readDataMode(): DataMode {
  const value = import.meta.env.VITE_DATA_MODE;
  if (value === 'live' || value === 'fallback' || value === 'fixture' || value === 'demo') {
    return value;
  }
  return 'fixture';
}

/** Modes whose sessions are real Supabase sessions rather than the fixture one. */
export function usesLiveAuthentication(mode: DataMode): boolean {
  return mode === 'live' || mode === 'demo';
}

export function readApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
}

export function isFixtureVisible(mode: DataMode, fallbackActive: boolean): boolean {
  return mode === 'fixture' || (mode === 'fallback' && fallbackActive);
}
