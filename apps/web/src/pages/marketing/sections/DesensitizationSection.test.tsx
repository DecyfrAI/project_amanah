import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DesensitizationSection } from './DesensitizationSection';

describe('DesensitizationSection', () => {
  it('explains why a longitudinal record matters', () => {
    render(<DesensitizationSection />);

    expect(
      screen.getByRole('heading', { name: /why longitudinal monitoring matters/i }),
    ).toBeVisible();
    expect(screen.getByText(/structured, reviewable record/i)).toBeVisible();
    expect(screen.getByText(/policymakers and researchers/i)).toBeVisible();
    expect(screen.getByText(/cohesive record across the sources we monitor/i)).toBeVisible();
    expect(screen.getByText(/that record is itself an amanah/i, { exact: false })).toBeVisible();
    expect(screen.getByText('Overview preview')).toBeVisible();
    expect(screen.queryByRole('heading', { name: /we used to be angry/i })).toBeNull();
    expect(screen.queryByText(/rarely appears as one isolated event/i)).toBeNull();
  });
});
