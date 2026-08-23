import { describe, expect, it } from 'vitest';

import { ENTRY_HEADLINES, ENTRY_TIPS } from './entry-copy';

describe('entry-copy', () => {
  it('keeps headlines short and tips as complete sentences', () => {
    expect(ENTRY_HEADLINES[0]).toBe('Insights await');
    expect(ENTRY_TIPS.length).toBeGreaterThan(3);
    expect(ENTRY_TIPS.every((tip) => tip.includes('.'))).toBe(true);
  });
});
