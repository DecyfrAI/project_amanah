import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProblemSection } from './ProblemSection';

describe('ProblemSection', () => {
  it('treats a single remark as already serious, not as something deniable', () => {
    render(<ProblemSection />);

    expect(screen.getByRole('heading', { name: /each comment already matters/i })).toBeVisible();
    expect(screen.getByText(/the feed will not keep it/i)).toBeVisible();
    expect(screen.getByText(/can already wound/i)).toBeVisible();
    expect(screen.queryByText(/deniable/i)).toBeNull();
    expect(screen.getAllByText(/classified as likely anti-Muslim hate/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'See more posts' })).toBeVisible();
  });
});
