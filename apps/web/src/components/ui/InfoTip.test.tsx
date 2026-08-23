import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { InfoTip } from './InfoTip';

describe('InfoTip', () => {
  it('uses a circled question mark and names the figure it explains', () => {
    render(<InfoTip label="Coverage">The window this view was collected for.</InfoTip>);

    expect(screen.getByRole('button', { name: 'About Coverage' })).toBeVisible();
    expect(screen.getByText('The window this view was collected for.')).toBeInTheDocument();
    expect(screen.queryByText('i')).toBeNull();
  });

  it('keeps the same accessible name when the mark sits on a card title', () => {
    render(
      <InfoTip label="Items collected" placement="card">
        Count of items collected in this window.
      </InfoTip>,
    );

    expect(screen.getByRole('button', { name: 'About Items collected' })).toBeVisible();
  });
});
