import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { MarketingHeader } from './MarketingHeader';

describe('MarketingHeader', () => {
  it('offers Log in and Sign up, and does not advertise the public dashboard', () => {
    render(
      <MemoryRouter>
        <MarketingHeader />
      </MemoryRouter>,
    );

    const loginLinks = screen.getAllByRole('link', { name: 'Log in' });
    expect(loginLinks.length).toBeGreaterThan(0);
    for (const link of loginLinks) {
      expect(link).toHaveAttribute('href', '/login');
    }

    const signupLinks = screen.getAllByRole('link', { name: 'Sign up' });
    expect(signupLinks.length).toBeGreaterThan(0);
    for (const link of signupLinks) {
      expect(link).toHaveAttribute('href', '/signup');
    }

    expect(screen.queryByRole('link', { name: /view dashboard/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /dashboard/i })).toBeNull();
  });

  it('uses short section labels that still point at the page anchors', () => {
    render(
      <MemoryRouter>
        <MarketingHeader />
      </MemoryRouter>,
    );

    const sections = [
      { name: 'Problem', href: '/#the-problem' },
      { name: 'Radicalization', href: '/#the-path' },
      { name: 'Why', href: '/#why-it-matters' },
      { name: 'Philosophy', href: '/#our-philosophy' },
      { name: 'Product', href: '/#what-it-does' },
      { name: 'How', href: '/#how-it-works' },
      { name: 'Responsible', href: '/#responsible-use' },
      { name: 'Method', href: '/#methodology' },
    ] as const;

    for (const section of sections) {
      const links = screen.getAllByRole('link', { name: section.name });
      expect(links.length).toBeGreaterThan(0);
      for (const link of links) {
        expect(link).toHaveAttribute('href', section.href);
      }
    }
  });
});
