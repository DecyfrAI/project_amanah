import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { InsightPage } from './InsightPage';

beforeEach(() => {
  resetFixtureProvider();
});

describe('InsightPage', () => {
  it('renders the fixture insight and its discussion', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/app/insights/ins_collective_blame']}>
          <Routes>
            <Route path="/app/insights/:insightId" element={<InsightPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole('heading', {
        name: /collective-blame share rose in the monitored youtube sample/i,
      }),
    ).toBeVisible();
    expect(screen.getByText(/23.7 percent/i)).toBeVisible();
    expect(await screen.findByRole('heading', { name: 'Discussion' })).toBeVisible();
  });
});
