import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DateRangePicker } from './DateRangePicker';

describe('DateRangePicker', () => {
  it('names the current window and applies a preset', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <DateRangePicker
        from="2026-07-18"
        to="2026-08-16"
        availableFrom="2026-06-18"
        availableTo="2026-08-16"
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /2026-07-18 to 2026-08-16/i }));
    await user.click(screen.getByRole('button', { name: /last 7 days/i }));

    expect(onChange).toHaveBeenCalledWith('2026-08-10', '2026-08-16');
  });

  it('refuses a day outside the collected range', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(
      <DateRangePicker
        from="2026-07-18"
        to="2026-08-16"
        availableFrom="2026-06-18"
        availableTo="2026-08-16"
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole('button', { name: /2026-07-18 to 2026-08-16/i }));

    expect(screen.getByRole('button', { name: /17 august 2026/i })).toBeDisabled();
    expect(onChange).not.toHaveBeenCalled();
  });
});
