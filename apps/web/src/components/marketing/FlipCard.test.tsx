import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { FlipCard } from './FlipCard';

function renderCard() {
  return render(
    <FlipCard
      name="No identity inference"
      summary="The system monitors sources and communities, never people."
      detail="It does not infer religion, build profiles, or rank individuals."
    />,
  );
}

describe('FlipCard', () => {
  it('exposes the whole card as one toggle button', () => {
    renderCard();

    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false');
  });

  it('reports its pressed state after being turned', async () => {
    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');

    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false');
  });

  it('can be turned from the keyboard', async () => {
    const user = userEvent.setup();
    renderCard();

    await user.tab();
    expect(screen.getByRole('button')).toHaveFocus();

    await user.keyboard('{Enter}');
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });

  it('announces the summary while face up and the detail once turned', async () => {
    const user = userEvent.setup();
    renderCard();

    // A button collapses its contents for assistive technology, so the
    // accessible name has to carry whichever face is showing.
    expect(screen.getByRole('button')).toHaveAccessibleName(
      /monitors sources and communities, never people/i,
    );

    await user.click(screen.getByRole('button'));

    expect(screen.getByRole('button')).toHaveAccessibleName(
      /does not infer religion, build profiles, or rank individuals/i,
    );
  });
});
