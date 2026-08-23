import { describe, expect, it } from 'vitest';

import { WORKSPACE_NAV } from '@/components/layout/navItems';

import { TOUR_STEPS } from './tour-steps';

describe('TOUR_STEPS', () => {
  it('walks every sidebar tab in order, then Profile, without jumping back', () => {
    const tabOrder = [...WORKSPACE_NAV.map((item) => item.to), '/app/profile'];

    for (const item of WORKSPACE_NAV) {
      expect(TOUR_STEPS.some((step) => step.to === item.to)).toBe(true);
    }

    expect(TOUR_STEPS.some((step) => step.id === 'profile' && step.to === '/app/profile')).toBe(
      true,
    );
    expect(TOUR_STEPS.some((step) => step.to === '/app/insights/ins_collective_blame')).toBe(false);

    const destinations = TOUR_STEPS.map((step) => step.to);
    let lastIndex = 0;
    for (const destination of destinations) {
      const index = tabOrder.indexOf(destination);
      expect(index).toBeGreaterThanOrEqual(lastIndex);
      lastIndex = index;
    }

    expect(new Set(TOUR_STEPS.map((step) => step.id)).size).toBe(TOUR_STEPS.length);
  });
});
