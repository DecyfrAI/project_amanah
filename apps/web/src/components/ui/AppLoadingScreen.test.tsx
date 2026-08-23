import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { ThemeProvider } from '@/app/ThemeProvider';

import { AppLoadingScreen } from './AppLoadingScreen';
import { ENTRY_TIPS } from './entry-copy';

afterEach(() => {
  document.documentElement.removeAttribute('data-theme');
  localStorage.removeItem('amanah.theme');
});

describe('AppLoadingScreen', () => {
  it('shows a single tip on the post-login hold, not the whole list', () => {
    render(
      <ThemeProvider>
        <MemoryRouter>
          <AppLoadingScreen hold />
        </MemoryRouter>
      </ThemeProvider>,
    );

    expect(screen.getByText(ENTRY_TIPS[0]!)).toBeVisible();
    expect(screen.queryByText(ENTRY_TIPS[1]!)).not.toBeInTheDocument();
    expect(screen.queryByText(ENTRY_TIPS[2]!)).not.toBeInTheDocument();
  });

  it('uses the inverse lockup when the stored theme is dark', () => {
    localStorage.setItem('amanah.theme', 'dark');

    render(
      <ThemeProvider>
        <MemoryRouter>
          <AppLoadingScreen />
        </MemoryRouter>
      </ThemeProvider>,
    );

    expect(screen.getByRole('img', { name: 'Project Amanah' })).toHaveAttribute(
      'src',
      '/brand/amanah-wordmark-inverse.png',
    );
  });
});
