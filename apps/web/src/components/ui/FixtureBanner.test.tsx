import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FixtureBanner } from './FixtureBanner';

describe('FixtureBanner', () => {
  it('states that the figures are synthetic in fixture mode', () => {
    render(<FixtureBanner />);

    expect(screen.getByRole('status')).toHaveTextContent(/these figures are synthetic/i);
  });
});
