import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { apiClient } from '@/api';
import { resetFixtureProvider } from '@/api/fixture-provider';

import { ContributionsPage } from './ContributionsPage';

function renderContributions() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ContributionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Saves one prepared report so the history has a row to show. */
async function savePreparedReport() {
  const analysis = await apiClient.analyzePolicies('itm_9b52');
  const candidate = analysis.candidates[0];
  if (candidate === undefined) {
    throw new Error('the fixture catalogue offered no policy to prepare against');
  }
  return apiClient.savePreparedReport({
    contentItemId: 'itm_9b52',
    platformPolicyId: candidate.platform_policy_id,
    policyVersion: candidate.version,
    evidenceSummary: 'Targets a religious group.',
    suggestedText: 'Please review this item.',
  });
}

afterEach(() => {
  resetFixtureProvider();
});

describe('ContributionsPage', () => {
  it('names the view in a single top-level heading', async () => {
    renderContributions();

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Your contributions' }),
    ).toBeVisible();
  });

  it('says an empty history is empty rather than showing nothing', async () => {
    renderContributions();

    expect(await screen.findByText(/have not contributed anything yet/i)).toBeVisible();
  });

  it('lists a saved report and shows it as prepared, not submitted', async () => {
    await savePreparedReport();
    renderContributions();

    expect(
      await screen.findByRole('heading', { level: 2, name: 'Prepared platform report' }),
    ).toBeVisible();
    // Prepared, never "sent": Amanah did not file it.
    expect(screen.getByText('prepared')).toBeVisible();
  });

  it('states that Amanah never submitted anything in this history', async () => {
    renderContributions();

    expect(await screen.findByText(/never submits a report to a platform/i)).toBeVisible();
  });
});
