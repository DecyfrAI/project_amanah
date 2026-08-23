import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ExplorerPage } from './ExplorerPage';

function renderExplorer(search = '/app/explorer') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[search]}>
        <ExplorerPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ExplorerPage', () => {
  it('names the view and shows excerpt wording in the table', async () => {
    renderExplorer();

    expect(await screen.findByRole('heading', { name: 'Explorer', level: 1 })).toBeVisible();
    expect(screen.getByText(/filter and search/i)).toBeVisible();
    expect(
      await screen.findByRole('table', { name: /comment rows show synthetic/i }),
    ).toBeVisible();
    expect(screen.getByText(/hand-reviewed examples/i)).toBeVisible();
  });

  it('shows the comment wording in the row, with no reveal control', async () => {
    renderExplorer('/app/explorer?from=2026-08-16&to=2026-08-16');

    const row = await screen.findByRole('row', { name: /item itm_4c1a/i });
    expect(
      within(row).getByText(
        /they should never have been allowed to build here, people like that do not belong/i,
      ),
    ).toBeVisible();
    expect(within(row).queryByRole('button', { name: /reveal/i })).toBeNull();
    expect(within(row).queryByText(/slur redacted/i)).toBeNull();
  });

  it('narrows the table when a type filter is in the URL', async () => {
    renderExplorer('/app/explorer?hate_type=threat');

    expect(await screen.findByText(/1 of 1 reviewed examples/i)).toBeVisible();
    const table = screen.getByRole('table', { name: /comment rows show synthetic/i });
    expect(within(table).getByRole('row', { name: /item itm_9b52/i })).toBeVisible();
    expect(within(table).getAllByRole('row')).toHaveLength(2);
  });

  it('filters the table when a type chip is pressed', async () => {
    const user = userEvent.setup();
    renderExplorer();

    await screen.findByRole('table', { name: /comment rows show synthetic/i });
    await user.click(screen.getByRole('button', { name: /threat or incitement/i }));

    expect(await screen.findByText(/1 of 1 reviewed examples/i)).toBeVisible();
    expect(screen.getByRole('row', { name: /item itm_9b52/i })).toBeVisible();
  });

  it('searches records by keyword and offers autocomplete', async () => {
    const user = userEvent.setup();
    renderExplorer();

    await screen.findByRole('table', { name: /comment rows show synthetic/i });
    const search = screen.getByLabelText('Search records');
    await user.type(search, 'prayer');

    const suggestion = document.querySelector('datalist option');
    expect(suggestion).toHaveValue('Council debates new prayer room planning application');

    await user.click(screen.getByRole('button', { name: 'Search' }));

    expect(await screen.findByText(/1 of 1 reviewed examples/i)).toBeVisible();
    expect(screen.getByRole('row', { name: /item itm_4c1a/i })).toBeVisible();
    expect(screen.queryByRole('row', { name: /item itm_9b52/i })).toBeNull();
  });

  it('shows image metadata on an image row, blurred until revealed', async () => {
    const user = userEvent.setup();
    renderExplorer('/app/explorer?q=img-ex-01');

    const row = await screen.findByRole('row', { name: /item itm_img_01/i });
    expect(within(row).getByText(/keep-calm style poster/i)).toBeVisible();
    expect(within(row).getByText(/img-ex-01.png/i)).toBeVisible();
    expect(within(row).getByText(/70,182 bytes/i)).toBeVisible();
    const reveal = within(row).getByRole('button', { name: 'Reveal image' });
    expect(reveal).toHaveAttribute('aria-expanded', 'false');
    await user.click(reveal);
    expect(reveal).toHaveAttribute('aria-expanded', 'true');
  });

  it('states that an empty result is not a quiet day', async () => {
    renderExplorer('/app/explorer?hate_type=threat&from=2026-06-18&to=2026-06-20');

    expect(await screen.findByText(/no reviewed examples match these filters/i)).toBeVisible();
    expect(screen.getByText(/not that the days were quiet/i)).toBeVisible();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
