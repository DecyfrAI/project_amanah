import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { HeroSection } from './HeroSection';

describe('HeroSection', () => {
  it('leads with Sign up and See how it works, not a third Log in', () => {
    render(
      <MemoryRouter>
        <HeroSection />
      </MemoryRouter>,
    );

    const actions = screen.getByRole('link', { name: 'Sign up' }).closest('div');
    expect(actions).not.toBeNull();
    expect(screen.getByRole('link', { name: 'Sign up' })).toHaveAttribute('href', '/signup');
    expect(screen.getByRole('link', { name: 'See how it works' })).toHaveAttribute(
      'href',
      '#what-it-does',
    );
    expect(actions?.querySelectorAll('a')).toHaveLength(2);
    expect(screen.queryByRole('link', { name: 'Log in' })).toBeNull();
    expect(screen.queryByRole('link', { name: /view dashboard/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /dashboard/i })).toBeNull();
  });
});
