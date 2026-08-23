import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DisplayHeading } from './DisplayHeading';

describe('DisplayHeading', () => {
  it('announces the two lines as one phrase', () => {
    render(<DisplayHeading level={2} upright="Why longitudinal" accent="monitoring matters." />);

    expect(
      screen.getByRole('heading', { name: 'Why longitudinal monitoring matters.' }),
    ).toBeVisible();
  });
});
