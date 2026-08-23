import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ExpandingPanels, type ExpandingPanel } from './ExpandingPanels';

const PANELS: readonly ExpandingPanel[] = [
  {
    id: 'watch',
    name: 'Watch',
    headline: 'Watch approved sources',
    body: 'Collect from approved sources.',
    outcome: 'A bounded sample',
  },
  {
    id: 'sort',
    name: 'Sort',
    headline: 'Sort relevance from stance',
    body: 'Separate relevance from stance.',
    outcome: 'Typed records',
  },
  {
    id: 'act',
    name: 'Act',
    headline: 'Route to a reviewer',
    body: 'Route to a human reviewer.',
    outcome: 'A decision',
  },
];

describe('ExpandingPanels', () => {
  it('opens the first panel by default', () => {
    render(<ExpandingPanels panels={PANELS} />);

    expect(screen.getByRole('button', { name: /watch/i })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Collect from approved sources.')).toBeVisible();
  });

  it('opens the panel that is chosen and closes the previous one', async () => {
    const user = userEvent.setup();
    render(<ExpandingPanels panels={PANELS} />);

    await user.click(screen.getByRole('button', { name: /sort/i }));

    expect(screen.getByRole('button', { name: /sort/i })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: /watch/i })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
    expect(screen.queryByText('Collect from approved sources.')).toBeNull();
  });

  it('keeps exactly one panel open', async () => {
    const user = userEvent.setup();
    render(<ExpandingPanels panels={PANELS} />);

    await user.click(screen.getByRole('button', { name: /act/i }));

    const expanded = screen
      .getAllByRole('button')
      .filter((button) => button.getAttribute('aria-expanded') === 'true');
    expect(expanded).toHaveLength(1);
  });

  it('ties each panel region back to the control that opens it', () => {
    render(<ExpandingPanels panels={PANELS} />);

    const trigger = screen.getByRole('button', { name: /watch/i });
    const region = screen.getByRole('region');

    expect(trigger).toHaveAttribute('aria-controls', region.id);
    expect(region).toHaveAttribute('aria-labelledby', trigger.id);
  });

  it('is operable from the keyboard', async () => {
    const user = userEvent.setup();
    render(<ExpandingPanels panels={PANELS} />);

    await user.tab();
    await user.tab();
    expect(screen.getByRole('button', { name: /sort/i })).toHaveFocus();

    await user.keyboard('{Enter}');
    expect(screen.getByText('Separate relevance from stance.')).toBeVisible();
  });
});
