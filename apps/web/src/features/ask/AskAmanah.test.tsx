import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { AskAmanah } from './AskAmanah';

function renderAsk() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AskAmanah />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AskAmanah', () => {
  it('answers a rate question from the stored figures', async () => {
    const user = userEvent.setup();
    renderAsk();

    await user.click(screen.getByRole('button', { name: 'Ask Amanah' }));
    expect(screen.getByRole('heading', { name: 'Ask Amanah' })).toBeVisible();
    expect(screen.getByText(/document retrieval is not connected/i)).toBeVisible();

    await user.type(
      screen.getByLabelText(/ask about this window/i),
      'What is the likely hate rate?',
    );
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    expect(await screen.findByText(/18\.7%/)).toBeVisible();
    expect(screen.getByText(/cited: likely hate rate/i)).toBeVisible();
    expect(screen.getByText(/not from a generated estimate/i)).toBeVisible();
  });

  it('offers starter questions and answers one from stored figures', async () => {
    const user = userEvent.setup();
    renderAsk();

    await user.click(screen.getByRole('button', { name: 'Ask Amanah' }));
    expect(screen.getByRole('button', { name: 'Trend over time' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'An explorer entry' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Current events' })).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'News and the rate' }));

    expect(await screen.findByText(/coinciding context/i)).toBeVisible();
    expect(screen.getByText(/not a cause/i)).toBeVisible();
  });
});
