import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { StageCarousel, type CarouselStage } from './StageCarousel';

const STAGES: readonly CarouselStage[] = [
  {
    id: 'first',
    name: 'Capture',
    summary: 'Collect the smallest unit that carries the finding.',
    detail: 'Authorized APIs only.',
    imageAlt: 'A courtyard.',
  },
  {
    id: 'second',
    name: 'Classify',
    summary: 'Establish relevance before stance.',
    detail: 'Uncertain cases abstain.',
    imageAlt: 'A tiled niche.',
  },
  {
    id: 'third',
    name: 'Review',
    summary: 'A reviewer confirms or corrects.',
    detail: 'Decisions append to the record.',
    imageAlt: 'A manuscript page.',
  },
];

function renderCarousel() {
  return render(<StageCarousel stages={STAGES} label="Evidence lifecycle" />);
}

describe('StageCarousel', () => {
  it('shows the first stage before any interaction', () => {
    renderCarousel();

    expect(screen.getByRole('tab', { name: /capture/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Collect the smallest unit that carries the finding.')).toBeVisible();
  });

  it('switches stage when a tab is clicked', async () => {
    const user = userEvent.setup();
    renderCarousel();

    await user.click(screen.getByRole('tab', { name: /classify/i }));

    expect(screen.getByRole('tab', { name: /classify/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Establish relevance before stance.')).toBeVisible();
    expect(screen.queryByText('Collect the smallest unit that carries the finding.')).toBeNull();
  });

  it('keeps only the selected tab in the tab order', async () => {
    const user = userEvent.setup();
    renderCarousel();

    expect(screen.getByRole('tab', { name: /capture/i })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: /classify/i })).toHaveAttribute('tabindex', '-1');

    await user.click(screen.getByRole('tab', { name: /classify/i }));

    expect(screen.getByRole('tab', { name: /capture/i })).toHaveAttribute('tabindex', '-1');
    expect(screen.getByRole('tab', { name: /classify/i })).toHaveAttribute('tabindex', '0');
  });

  it('moves between stages with the arrow keys', async () => {
    const user = userEvent.setup();
    renderCarousel();

    await user.tab();
    expect(screen.getByRole('tab', { name: /capture/i })).toHaveFocus();

    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: /classify/i })).toHaveFocus();
    expect(screen.getByText('Establish relevance before stance.')).toBeVisible();
  });

  it('wraps from the last stage back to the first', async () => {
    const user = userEvent.setup();
    renderCarousel();

    await user.tab();
    await user.keyboard('{End}');
    expect(screen.getByRole('tab', { name: /review/i })).toHaveFocus();

    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: /capture/i })).toHaveFocus();
  });

  it('disables the previous control on the first stage and next on the last', async () => {
    const user = userEvent.setup();
    renderCarousel();

    expect(screen.getByRole('button', { name: 'Previous stage' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next stage' })).toBeEnabled();

    await user.click(screen.getByRole('tab', { name: /review/i }));

    expect(screen.getByRole('button', { name: 'Previous stage' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Next stage' })).toBeDisabled();
  });

  it('advances with the next control', async () => {
    const user = userEvent.setup();
    renderCarousel();

    await user.click(screen.getByRole('button', { name: 'Next stage' }));

    expect(screen.getByText('Establish relevance before stance.')).toBeVisible();
  });

  it('describes the artwork rather than the stage in the image alt text', () => {
    renderCarousel();

    expect(screen.getByRole('img')).toHaveAccessibleName('A courtyard.');
  });

  it('ties the panel to its tab for assistive technology', () => {
    renderCarousel();

    const panel = screen.getByRole('tabpanel');
    const tab = screen.getByRole('tab', { name: /capture/i });

    expect(panel).toHaveAttribute('aria-labelledby', tab.id);
    expect(tab).toHaveAttribute('aria-controls', panel.id);
  });
});
