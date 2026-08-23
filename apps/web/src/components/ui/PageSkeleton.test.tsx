import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PageSkeleton } from './PageSkeleton';

describe('PageSkeleton', () => {
  it('exposes the wait as a polite status region', () => {
    render(<PageSkeleton label="Overview" />);

    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveAttribute('aria-busy', 'true');
  });

  it('names what is loading rather than announcing a bare "loading"', () => {
    render(<PageSkeleton label="Explorer" />);

    expect(screen.getByText('Loading Explorer')).toBeInTheDocument();
  });
});
