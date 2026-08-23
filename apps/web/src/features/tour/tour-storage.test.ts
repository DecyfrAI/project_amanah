import { describe, expect, it } from 'vitest';

import {
  clearTourCompletion,
  readTourCompletion,
  TOUR_STORAGE_KEY,
  writeTourCompletion,
} from './tour-storage';

describe('tour-storage', () => {
  it('round-trips a completion status', () => {
    localStorage.removeItem(TOUR_STORAGE_KEY);
    expect(readTourCompletion()).toBeNull();
    expect(writeTourCompletion('done')).toBe(true);
    expect(readTourCompletion()).toBe('done');
  });

  it('clears a prior finish so a new signup can auto-open', () => {
    writeTourCompletion('skipped');
    clearTourCompletion();
    expect(readTourCompletion()).toBeNull();
  });
});
