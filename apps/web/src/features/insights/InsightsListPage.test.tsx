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

  it('contains no unrelated image feed (PA-02)', async () => {
    renderList();

    expect(await screen.findByRole('heading', { name: 'Insights', level: 1 })).toBeVisible();
    // The unscoped Image Evidence section queried an unfiltered Explorer page
    // for anything with an image; it was removed because those images were not
    // tied to any insight. Media may appear only inside the discussion it
    // belongs to.
    expect(screen.queryByRole('heading', { name: 'Image evidence' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Reveal image' })).toBeNull();
  });
});
