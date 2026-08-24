import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { ItemDetailPage } from './ItemDetailPage';

function renderItem(itemId: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/app/explorer/${itemId}`]}>
        <Routes>
          <Route path="/app/explorer/:itemId" element={<ItemDetailPage />} />
          <Route path="/app/explorer" element={<p>Explorer list</p>} />
          <Route path="/app/reports" element={<p>Reports destination</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  resetFixtureProvider();
});

describe('ItemDetailPage', () => {
  it('shows the item with its classification and model disclosure', async () => {
    renderItem('itm_9b52');

    expect(await screen.findByRole('heading', { level: 2, name: 'Classification' })).toBeVisible();
    expect(screen.getByRole('heading', { level: 2, name: 'Model disclosure' })).toBeVisible();
    expect(screen.getByText('Taxonomy version')).toBeVisible();
    expect(screen.getByText('Prompt version')).toBeVisible();
  });

  it('states the sampling limitation beside the figures', async () => {
    renderItem('itm_9b52');

    expect(await screen.findByRole('heading', { level: 2, name: 'Limitations' })).toBeVisible();
    expect(screen.getByText(/not a platform, a country, or a group of people/i)).toBeVisible();
  });

  it('exposes no author or person-level field', async () => {
    renderItem('itm_9b52');

    await screen.findByRole('heading', { level: 2, name: 'Classification' });
    expect(screen.queryByText(/author/i)).toBeNull();
    expect(screen.queryByText(/handle/i)).toBeNull();
  });

  it('offers report preparation without implying Amanah sends it', async () => {
    renderItem('itm_9b52');

    expect(await screen.findByRole('link', { name: 'Prepare a report' })).toHaveAttribute(
      'href',
      '/app/reports?item=itm_9b52',
    );
    expect(screen.getByText(/Amanah never submits a report/i)).toBeVisible();
  });

  it('reports a missing item as an error rather than an empty page', async () => {
    renderItem('itm_does_not_exist');

    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be found/i);
  });
});
