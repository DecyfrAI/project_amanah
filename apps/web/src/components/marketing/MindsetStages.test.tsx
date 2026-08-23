import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { MindsetStages } from './MindsetStages';

describe('MindsetStages', () => {
  it('walks Borum four stages without claiming a comment caused an attack', async () => {
    const user = userEvent.setup();
    render(<MindsetStages />);

    expect(screen.getByRole('button', { name: /grievance/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByText(/a grievance is not yet a target/i)).toBeVisible();

    await user.click(screen.getByRole('button', { name: /distancing/i }));

    expect(screen.getByRole('button', { name: /distancing/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByText(/distance makes cruelty cheaper/i)).toBeVisible();
    expect(screen.getByRole('link', { name: /Randy Borum/i })).toHaveAttribute('target', '_blank');
    expect(screen.queryByRole('button', { name: /about four-stage/i })).toBeNull();
    expect(document.body.textContent).not.toMatch(/caused by/i);
  });
});
