import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { DashboardPreview } from './DashboardPreview';

describe('DashboardPreview', () => {
  it('shows the window total with its numerator and denominator', () => {
    render(<DashboardPreview />);

    expect(screen.getByText('Overview preview')).toBeVisible();
    expect(screen.getByText('74 of 312')).toBeVisible();
    expect(screen.getByText(/23.7 percent across the window/i)).toBeVisible();
    expect(screen.getByText(/8 of 8 collection days ran in this window/i)).toBeVisible();
  });

  it('switches the charted metric', async () => {
    const user = userEvent.setup();
    render(<DashboardPreview />);

    const rate = screen.getByRole('button', { name: 'Rate' });
    const volume = screen.getByRole('button', { name: 'Volume' });

    expect(rate).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Likely-hate rate among relevant items')).toBeVisible();

    await user.click(volume);

    expect(volume).toHaveAttribute('aria-pressed', 'true');
    expect(rate).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByText('Relevant items collected each day')).toBeVisible();
  });

  it('reads out the counts behind the day a reader selects', async () => {
    const user = userEvent.setup();
    render(<DashboardPreview />);

    expect(
      screen.getByText(/12 of 39 relevant items classified as likely hate, 30.8 percent/i),
    ).toBeVisible();

    await user.click(screen.getByRole('button', { name: '11 Aug' }));

    expect(
      screen.getByText(/8 of 42 relevant items classified as likely hate, 19.0 percent/i),
    ).toBeVisible();
  });

  it('offers the same figures as a table', async () => {
    const user = userEvent.setup();
    render(<DashboardPreview />);

    await user.click(screen.getByText(/show these numbers as a table/i));

    expect(screen.getByRole('table', { name: /daily counts and likely-hate rate/i })).toBeVisible();
    expect(screen.getByRole('rowheader', { name: '11 Aug' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Relevant' })).toBeVisible();
  });
});
