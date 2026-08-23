import { describe, expect, it } from 'vitest';

import { bubbleDiameter, donutSlices } from './breakdown-geometry';

describe('donutSlices', () => {
  it('walks the circumference in count order', () => {
    const slices = donutSlices(
      [
        { key: 'a', count: 3 },
        { key: 'b', count: 1 },
      ],
      4,
      100,
    );

    expect(slices[0]).toEqual({ key: 'a', length: 75, offset: 0 });
    expect(slices[1]).toEqual({ key: 'b', length: 25, offset: 75 });
  });

  it('treats a zero total as empty marks, not a full ring', () => {
    const slices = donutSlices([{ key: 'a', count: 0 }], 0, 100);
    expect(slices[0]?.length).toBe(0);
  });
});

describe('bubbleDiameter', () => {
  it('gives the largest count the largest disc', () => {
    expect(bubbleDiameter(16, 16, 20, 80)).toBe(80);
    expect(bubbleDiameter(4, 16, 20, 80)).toBe(50);
  });

  it('never collapses a present row to nothing', () => {
    expect(bubbleDiameter(0, 16, 20, 80)).toBe(20);
  });
});
