import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { DiscussionPanel } from './DiscussionPanel';

beforeEach(() => {
  resetFixtureProvider();
});

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DiscussionPanel insightId="ins_collective_blame" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('DiscussionPanel', () => {
  it('shows the seeded note and the capture deep link', async () => {
    renderPanel();

    expect(await screen.findByRole('heading', { name: 'Discussion' })).toBeVisible();
    expect(screen.getByText(/gap days as gaps/i)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Open this view' })).toHaveAttribute(
      'href',
      '/app/explorer?from=2026-08-01&to=2026-08-16&narrative=collective_blame',
    );
  });

  it('records a useful reaction on an existing note', async () => {
    const user = userEvent.setup();
    renderPanel();

    const usefulButtons = await screen.findAllByRole('button', { name: /useful/i });
    const useful = usefulButtons[0];
    if (useful === undefined) {
      throw new Error('Expected a Useful button on the first note.');
    }
    await user.click(useful);

    expect(useful).toHaveAttribute('aria-pressed', 'true');
  });

  it('posts a note and lets the author retract it', async () => {
    const user = userEvent.setup();
    renderPanel();

    await screen.findByRole('heading', { name: 'Discussion' });
    await user.type(
      screen.getByLabelText('Add a note'),
      'The rate uses relevant items as the denominator.',
    );
    await user.click(screen.getByRole('button', { name: 'Post note' }));

    expect(
      await screen.findByText('The rate uses relevant items as the denominator.'),
    ).toBeVisible();

    const retractButtons = screen.getAllByRole('button', { name: 'Retract this note' });
    const latestRetract = retractButtons[retractButtons.length - 1];
    if (latestRetract === undefined) {
      throw new Error('Expected a Retract control on the note just posted.');
    }
    await user.click(latestRetract);
    expect(await screen.findByText('This note was retracted.')).toBeVisible();
  });
});
