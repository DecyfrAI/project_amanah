import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { MarketingFooter } from './MarketingFooter';

describe('MarketingFooter', () => {
  it('places the mosque photograph behind the closing invitation', () => {
    render(
      <MemoryRouter>
        <MarketingFooter />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: /carry the trust with care/i })).toBeVisible();

    const photograph = document.querySelector('img[src="/media/closing-mosque.webp"]');
    expect(photograph).toBeInstanceOf(HTMLImageElement);
    expect(photograph).toHaveAttribute('width', '1024');
    expect(photograph).toHaveAttribute('height', '576');
  });

  it('lists the same sections as the page argument', () => {
    render(
      <MemoryRouter>
        <MarketingFooter />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Why' })).toHaveAttribute('href', '/#why-it-matters');
    expect(screen.getByRole('link', { name: 'Radicalization' })).toHaveAttribute(
      'href',
      '/#the-path',
    );
    expect(screen.getByRole('link', { name: 'Responsible' })).toHaveAttribute(
      'href',
      '/#responsible-use',
    );
    expect(screen.getByRole('link', { name: 'Sign up' })).toHaveAttribute('href', '/signup');
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login');
    expect(screen.queryByRole('link', { name: 'Read the methodology' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Lessons and support' })).toBeNull();
    expect(screen.queryByRole('link', { name: /view dashboard/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /dashboard/i })).toBeNull();
  });

  it('credits the year, the monitoring tagline, and the Harvest hackathon', () => {
    render(
      <MemoryRouter>
        <MarketingFooter />
      </MemoryRouter>,
    );

    const year = new Date().getFullYear();
    expect(
      screen.getByText(
        `© ${year} Project Amanah, Monitoring Anti-Muslim Hate Online, The Harvest Anti-Muslim Hate Hackathon`,
      ),
    ).toBeVisible();
    expect(screen.getByRole('link', { name: 'Decyfr AI' })).toHaveAttribute(
      'href',
      'https://decyfrai.com/',
    );
  });
});
