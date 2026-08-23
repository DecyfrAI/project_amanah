/**
 * First-visit workspace tour persistence (fixture-first).
 *
 * When a profile API exists, this key becomes a mirror of onboarding_status.
 * Until then localStorage is honest about what it can remember.
 */

export const TOUR_STORAGE_KEY = 'amanah.workspace-tour';
export const TOUR_OPEN_EVENT = 'amanah:open-workspace-tour';

export type TourCompletion = 'done' | 'skipped';

export function readTourCompletion(): TourCompletion | null {
  try {
    const value = localStorage.getItem(TOUR_STORAGE_KEY);
    if (value === 'done' || value === 'skipped') {
      return value;
    }
    return null;
  } catch {
    return null;
  }
}

/** Returns false when the preference could not be written. */
export function writeTourCompletion(status: TourCompletion): boolean {
  try {
    localStorage.setItem(TOUR_STORAGE_KEY, status);
    return true;
  } catch {
    return false;
  }
}

/** Clears a prior skip or finish so the next workspace visit auto-opens. */
export function clearTourCompletion(): void {
  try {
    localStorage.removeItem(TOUR_STORAGE_KEY);
  } catch {
    // Storage can throw in a locked-down browser. The tour then stays closed.
  }
}

/** Opens or replays the tour from Help / Settings without clearing completion yet. */
export function requestWorkspaceTour(): void {
  window.dispatchEvent(new CustomEvent(TOUR_OPEN_EVENT));
}
