import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { PathSection } from './PathSection';

describe('PathSection', () => {
  it('describes a path without claiming a comment caused an attack', () => {
    render(<PathSection />);

    expect(screen.getByRole('heading', { name: /a handle is not a face/i })).toBeVisible();
    expect(screen.getByText(/lowers the cost of saying it/i)).toBeVisible();
    expect(screen.getByText(/4chan and 8chan/i)).toBeVisible();
    expect(screen.getByText(/does not send anyone there/i)).toBeVisible();
    expect(screen.getByText(/placed next to events in the same window/i)).toBeVisible();
    expect(screen.queryByText(/caused by/i)).toBeNull();
    expect(
      screen.getByRole('img', { name: /silhouette of a person facing a bright screen/i }),
    ).toBeVisible();
    expect(screen.queryByText(/a handle is not a face. the photograph/i)).toBeNull();
  });

  it('opens the four-stage model from the path carousel', async () => {
    const user = userEvent.setup();
    render(<PathSection />);

    await user.click(screen.getByRole('tab', { name: 'The model' }));

    expect(screen.getByRole('button', { name: /grievance/i })).toBeVisible();
    expect(screen.getByRole('link', { name: /Randy Borum/i })).toBeVisible();
  });
});
