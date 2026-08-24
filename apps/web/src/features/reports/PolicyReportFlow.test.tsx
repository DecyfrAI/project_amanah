import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { PolicyReportFlow } from './PolicyReportFlow';

function renderFlow(path = '/app/reports') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <PolicyReportFlow />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Reads the catalogue for a classified item that has policy candidates. */
async function analyzeItem(user: ReturnType<typeof userEvent.setup>, itemId = 'itm_9b52') {
  await user.type(screen.getByLabelText('Item reference'), itemId);
  await user.click(screen.getByRole('button', { name: 'Find matching policies' }));
}

afterEach(() => {
  resetFixtureProvider();
});

describe('PolicyReportFlow', () => {
  it('shows each candidate with its official link, version, and last-reviewed date', async () => {
    const user = userEvent.setup();
    renderFlow();

    await analyzeItem(user);

    expect(await screen.findByRole('radio', { name: 'Hate speech policy' })).toBeVisible();
    expect(screen.getByText(/version 2026-05/i)).toBeVisible();
    // Every candidate carries its own last-reviewed date, so several match.
    expect(screen.getAllByText(/last reviewed 2026-08-01/i).length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole('link', { name: /Read the platform's own rule/i })[0],
    ).toHaveAttribute('href', 'https://support.google.com/youtube/answer/2801939');
  });

  it('carries the uncertainty disclosure with the candidates', async () => {
    const user = userEvent.setup();
    renderFlow();

    await analyzeItem(user);

    expect(await screen.findByText(/possible policy matches, not findings/i)).toBeVisible();
    expect(screen.getByText(/Amanah never submits one/i)).toBeVisible();
  });

  it('refuses to save until a policy version is explicitly confirmed', async () => {
    const user = userEvent.setup();
    renderFlow();

    await analyzeItem(user);
    await user.click(await screen.findByRole('radio', { name: 'Hate speech policy' }));
    await user.type(screen.getByLabelText('Evidence summary'), 'Targets a religious group.');
    await user.type(screen.getByLabelText('Wording you would send'), 'Please review this item.');
    await user.click(screen.getByRole('button', { name: 'Save prepared report' }));

    expect(screen.getByText(/confirm the version you read/i)).toBeVisible();
    expect(screen.queryByText(/Saved to your contributions/i)).toBeNull();
  });

  it('saves a confirmed report and never claims the platform received it', async () => {
    const user = userEvent.setup();
    renderFlow();

    await analyzeItem(user);
    await user.click(await screen.findByRole('radio', { name: 'Hate speech policy' }));
    await user.type(screen.getByLabelText('Evidence summary'), 'Targets a religious group.');
    await user.type(screen.getByLabelText('Wording you would send'), 'Please review this item.');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Save prepared report' }));

    expect(await screen.findByText(/Saved to your contributions/i)).toBeVisible();
    expect(screen.getByText(/Amanah did not submit this report/i)).toBeVisible();
    // The only submission control records what the *user* says they did.
    expect(screen.getByRole('button', { name: 'I filed this myself' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /^send$/i })).toBeNull();
  });

  it('offers no policy for an item that was not classified as hate', async () => {
    const user = userEvent.setup();
    renderFlow();

    await analyzeItem(user, 'itm_1d05');

    expect(await screen.findByText(/does not suggest a rule for counterspeech/i)).toBeVisible();
    expect(screen.queryByRole('radio')).toBeNull();
  });
});
