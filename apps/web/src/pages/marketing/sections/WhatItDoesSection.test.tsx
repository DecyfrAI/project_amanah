import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { WhatItDoesSection } from './WhatItDoesSection';

describe('WhatItDoesSection', () => {
  it('states the goal of a unified observatory for policymakers and researchers', () => {
    render(<WhatItDoesSection />);

    expect(screen.getByRole('heading', { name: /not another feed/i })).toBeVisible();
    expect(screen.getByText(/one platform for the sources we are allowed to watch/i)).toBeVisible();
    expect(screen.getByText(/policymakers, researchers/i)).toBeVisible();
    expect(screen.getByText(/how the pattern evolves over time/i)).toBeVisible();
    expect(screen.getByText(/study how it takes root/i)).toBeVisible();
    expect(screen.getByText(/does not treat that as proof of a cause/i)).toBeVisible();
  });

  it('accounts for insights, image evidence, search, lessons, and image labeling', () => {
    render(<WhatItDoesSection />);

    expect(screen.getByRole('button', { name: /insights/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /lessons/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /explorer/i })).toBeVisible();
    expect(screen.getByRole('button', { name: /review/i })).toBeVisible();
    expect(screen.queryByRole('link', { name: /lessons/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /dashboard/i })).toBeNull();
  });
});
