import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ThemeProvider } from '@/app/ThemeProvider';
import { DataModeProvider } from '@/app/DataModeProvider';
import { clearMockDataPreference } from '@/api';
import { endFixtureSession, hasFixtureSession, startFixtureSession } from '@/features/auth/session';
import { SessionProvider } from '@/features/auth/SessionProvider';
import { TOUR_STORAGE_KEY, writeTourCompletion } from '@/features/tour/tour-storage';

import { AppShell } from './AppShell';

function withProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <DataModeProvider>
        <SessionProvider>
          <ThemeProvider>{ui}</ThemeProvider>
        </SessionProvider>
      </DataModeProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  // AppShell mounts the first-visit tour; keep it closed for chrome tests.
  writeTourCompletion('done');
});

afterEach(() => {
  clearMockDataPreference();
  endFixtureSession();
  document.documentElement.removeAttribute('data-theme');
  localStorage.removeItem(TOUR_STORAGE_KEY);
  localStorage.removeItem('amanah.sidebar-collapsed');
  localStorage.removeItem('amanah.theme');
});

function renderProfileRoute(initialPath = '/app') {
  return render(
    withProviders(
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<h1>Overview</h1>} />
            <Route path="profile" element={<h1>Profile and account</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    ),
  );
}

function renderShell(initialPath = '/app') {
  return render(
    withProviders(
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<h1>Overview</h1>} />
            <Route path="review" element={<h1>Review</h1>} />
          </Route>
          <Route path="/" element={<p>Marketing page</p>} />
        </Routes>
      </MemoryRouter>,
    ),
  );
}

describe('AppShell', () => {
  it('lists every workspace tab and marks the current one', () => {
    renderShell();

    const nav = screen.getAllByRole('navigation', { name: 'Workspace' })[0];
    expect(nav).toBeDefined();

    for (const label of [
      'Overview',
      'Explorer',
      'Insights',
      'Lessons',
      'Review',
      'Reports',
      'Connections',
      'Settings',
    ]) {
      expect(screen.getAllByRole('link', { name: label }).length).toBeGreaterThan(0);
    }

    const current = screen.getAllByRole('link', { name: 'Overview' })[0];
    expect(current).toHaveAttribute('aria-current', 'page');
  });

  it('uses the stacked lockup in the expanded sidebar', () => {
    renderShell();

    const wordmark = screen.getAllByRole('img', { name: 'Project Amanah' })[0];
    expect(wordmark).toHaveAttribute('src', '/brand/amanah-stacked.png');
  });

  it('names the signed-in reviewer', () => {
    startFixtureSession('Amina R.');
    renderShell();

    // Named in the sidebar identity block, the top bar, and the mobile drawer.
    expect(screen.getAllByText('Amina R.').length).toBeGreaterThanOrEqual(2);
  });

  it('puts the mock-data switch in the top bar', () => {
    renderShell();

    expect(screen.getByRole('switch', { name: 'Mock data' })).toBeVisible();
  });

  it('moves between tabs without leaving the shell', async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getAllByRole('link', { name: 'Review' })[0]!);

    expect(screen.getByRole('heading', { name: 'Review' })).toBeVisible();
    expect(screen.getAllByRole('link', { name: 'Overview' }).length).toBeGreaterThan(0);
  });

  it('ends the session on log out', async () => {
    const user = userEvent.setup();
    startFixtureSession();
    renderShell();

    await user.click(screen.getByRole('button', { name: /log out/i }));

    expect(hasFixtureSession()).toBe(false);
    expect(screen.getByText('Marketing page')).toBeVisible();
  });

  it('switches the theme from the sidebar', async () => {
    const user = userEvent.setup();
    renderShell();

    expect(document.documentElement.dataset.theme).toBe('light');

    await user.click(screen.getAllByRole('button', { name: /switch to dark theme/i })[0]!);

    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('collapses the sidebar while keeping every tab named', async () => {
    const user = userEvent.setup();
    renderShell();

    const collapse = screen.getByRole('button', { name: /collapse sidebar/i });
    expect(collapse).toHaveAttribute('aria-expanded', 'true');

    await user.click(collapse);

    const expand = screen.getByRole('button', { name: /expand sidebar/i });
    expect(expand).toHaveAttribute('aria-expanded', 'false');
    // Labels are hidden visually, not removed, so the rail stays navigable.
    expect(screen.getAllByRole('link', { name: 'Explorer' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('link', { name: 'Settings' }).length).toBeGreaterThan(0);
  });

  it('keeps the collapse control as a chevron rather than a pane mark', () => {
    renderShell();

    const collapse = screen.getByRole('button', { name: /collapse sidebar/i });
    const paths = collapse.querySelectorAll('svg path');
    expect(paths).toHaveLength(1);
  });

  it('opens Ask Amanah from the corner control', async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole('button', { name: 'Ask Amanah' }));

    expect(screen.getByRole('heading', { name: 'Ask Amanah' })).toBeVisible();
    expect(screen.getByText(/stored figures for this sample/i)).toBeVisible();
  });

  it('opens the workspace tour from Tour', async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole('button', { name: 'Tour' }));

    expect(screen.getByRole('heading', { name: 'The workspace', level: 2 })).toBeVisible();
    expect(screen.getByText(/^1 \/ \d+$/)).toBeVisible();
  });

  it('reaches the profile from both the sidebar and the top bar', async () => {
    const user = userEvent.setup();
    startFixtureSession('Amina R.', 'amina@example.org');
    renderProfileRoute();

    const profileLinks = screen.getAllByRole('link', { name: /amina r\./i });
    expect(profileLinks.length).toBeGreaterThanOrEqual(2);

    await user.click(profileLinks[0]!);

    expect(screen.getByRole('heading', { name: /profile and account/i })).toBeVisible();
  });
});
