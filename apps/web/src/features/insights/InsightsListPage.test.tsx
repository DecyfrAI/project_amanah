import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { InsightsListPage } from './InsightsListPage';

function renderList() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <InsightsListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('InsightsListPage', () => {
  it('renders each insight as a card with the counts it rests on', async () => {
    renderList();

    expect(await screen.findByRole('heading', { name: 'Insights', level: 1 })).toBeVisible();

    const card = screen.getByRole('article', {
      name: /collective-blame share rose in the monitored youtube sample/i,
    });
    expect(within(card).getByText(/not a prevalence estimate/i)).toBeVisible();
    expect(within(card).getByText(/312 of 1,483/)).toBeVisible();
    expect(
      within(card).getByRole('link', {
        name: /collective-blame share rose in the monitored youtube sample/i,
      }),
    ).toHaveAttribute('href', '/app/insights/ins_collective_blame');
    expect(within(card).getByText('Machine-generated')).toBeVisible();
  });

  it('shows image posts with file metadata instead of a comment', async () => {
    renderList();

    expect(await screen.findByRole('heading', { name: 'Image evidence' })).toBeVisible();
    expect(await screen.findByText(/img-ex-01.png/i)).toBeVisible();
    expect(screen.getByText(/70,182 bytes/i)).toBeVisible();
    expect(screen.getAllByRole('button', { name: 'Reveal image' }).length).toBeGreaterThan(0);
  });
});
