import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { ReviewPage } from './ReviewPage';

beforeEach(() => {
  resetFixtureProvider();
});

function renderReview() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ReviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** The severity-3 escalation sorts first, since the queue is priority-ordered. */
async function topQueueItem(): Promise<HTMLElement> {
  return await screen.findByRole('article', { name: /post replying to a national headline/i });
}

describe('ReviewPage', () => {
  it('names the view in a single top-level heading', async () => {
    renderReview();

    expect(await screen.findByRole('heading', { level: 1, name: 'Review queue' })).toBeVisible();
  });

  it('says that a decision appends beside the prediction rather than replacing it', async () => {
    renderReview();

    expect(await screen.findByText(/never overwrites it/i)).toBeVisible();
  });

  it('orders the queue by priority, so an escalation outranks low confidence', async () => {
    renderReview();

    const queue = await screen.findByRole('list', { name: 'Awaiting a decision' });
    const items = within(queue).getAllByRole('article');
    expect(items[0]).toHaveAccessibleName(/post replying to a national headline/i);
  });

  it('states the queue counts against what they came out of', async () => {
    renderReview();

    expect(await screen.findByText('6 of 1,208 classified items in the window')).toBeVisible();
    // No decision has been recorded, so agreement refuses to state a percentage
    // rather than dividing by zero or implying a reading.
    expect(screen.getByText('No decision has been recorded yet.')).toBeVisible();
    expect(screen.getByText('Not yet')).toBeVisible();
  });

  it('labels the review state in words, not by colour alone', async () => {
    renderReview();

    expect(within(await topQueueItem()).getByText('Awaiting review')).toBeVisible();
  });

  it('shows the comment wording on every queue item, with no reveal control', async () => {
    renderReview();

    const item = await topQueueItem();
    expect(within(item).getByText(/someone should make them leave before the vote/i)).toBeVisible();
    expect(within(item).queryByRole('button', { name: /reveal/i })).toBeNull();
    expect(screen.queryByText(/slur redacted/i)).toBeNull();
    expect(screen.getByText(/those people are not to be believed/i)).toBeVisible();
  });

  it('presents the model score as a score, with its confidence tier in words', async () => {
    renderReview();

    expect(within(await topQueueItem()).getByText('0.91 (high confidence)')).toBeVisible();
  });

  it('requires a claim before a decision, and says why', async () => {
    renderReview();

    const item = within(await topQueueItem());
    expect(item.getByRole('button', { name: 'Claim to review' })).toBeEnabled();
    expect(item.getByText(/a claim is a lease for 30 minutes/i)).toBeVisible();
    expect(item.queryByRole('button', { name: 'Confirm label' })).toBeNull();
  });

  it('offers the three decisions once a task is claimed', async () => {
    const user = userEvent.setup();
    renderReview();

    const item = within(await topQueueItem());
    await user.click(item.getByRole('button', { name: 'Claim to review' }));

    expect(await item.findByRole('button', { name: 'Confirm label' })).toBeEnabled();
    expect(item.getByRole('button', { name: 'Correct label' })).toBeEnabled();
    expect(item.getByRole('button', { name: 'Needs context' })).toBeEnabled();
    expect(item.getByText('Claimed by you')).toBeVisible();
  });

  it('appends a confirmation beside the prediction, leaving the proposal on screen', async () => {
    const user = userEvent.setup();
    renderReview();

    const item = within(await topQueueItem());
    await user.click(item.getByRole('button', { name: 'Claim to review' }));
    await user.click(await item.findByRole('button', { name: 'Confirm label' }));

    expect(await item.findByText(/Confirmed the proposed label/)).toBeVisible();
    // The model's proposal is still there: a decision appends, never replaces.
    expect(item.getByText('Classified as likely anti-Muslim hate')).toBeVisible();
    expect(item.getByText('0.91 (high confidence)')).toBeVisible();
    expect(item.getByText('Decided')).toBeVisible();
  });

  it('records a correction with its labels and says the prediction is unchanged', async () => {
    const user = userEvent.setup();
    renderReview();

    const item = within(await topQueueItem());
    await user.click(item.getByRole('button', { name: 'Claim to review' }));
    await user.click(await item.findByRole('button', { name: 'Correct label' }));

    await user.selectOptions(item.getByLabelText('Corrected stance'), 'counterspeech_or_quotation');
    await user.selectOptions(item.getByLabelText('Corrected severity'), '0');
    await user.click(item.getByRole('button', { name: 'Record correction' }));

    const appended = await item.findByText(/Corrected the proposed label/);
    expect(appended).toBeVisible();
    expect(item.getByText(/The model's proposal above is unchanged/)).toBeVisible();
  });

  it('returns a needs-context item to the queue rather than closing it', async () => {
    const user = userEvent.setup();
    renderReview();

    const item = within(await topQueueItem());
    await user.click(item.getByRole('button', { name: 'Claim to review' }));
    await user.click(await item.findByRole('button', { name: 'Needs context' }));

    expect(await item.findByText(/Returned to the queue for context/)).toBeVisible();
    // Still open, so it can be claimed again rather than being settled.
    expect(item.getByRole('button', { name: 'Claim to review' })).toBeEnabled();
  });

  it('offers the training-candidate flag on a correction only', async () => {
    const user = userEvent.setup();
    renderReview();

    const item = within(await topQueueItem());
    await user.click(item.getByRole('button', { name: 'Claim to review' }));

    expect(item.queryByText(/training-candidate pool/i)).toBeNull();

    await user.click(await item.findByRole('button', { name: 'Correct label' }));

    expect(item.getByText(/nothing\s+retrains or activates a model from it/i)).toBeVisible();
  });

  it('does not host the report-draft form on Review', async () => {
    renderReview();

    await screen.findByRole('heading', { level: 1, name: 'Review queue' });
    expect(screen.queryByLabelText('Screenshot')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Generate draft' })).toBeNull();
    expect(screen.queryByLabelText('Report platform')).toBeNull();
    expect(screen.getByLabelText('Research image')).toBeVisible();
    expect(screen.getByText('Drop a research image here')).toBeVisible();
  });

  it('lists research examples blurred until a person reveals one', async () => {
    renderReview();

    expect(await screen.findByRole('heading', { name: 'Research image examples' })).toBeVisible();
    const reveals = await screen.findAllByRole('button', { name: 'Reveal example' });
    expect(reveals.length).toBe(42);
    expect(reveals[0]).toHaveAttribute('aria-expanded', 'false');
  });

  it('routes Prepare a report to Reports instead of opening a form here', async () => {
    const user = userEvent.setup();
    const client = new QueryClient({
      defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/app/review']}>
          <Routes>
            <Route path="/app/review" element={<ReviewPage />} />
            <Route path="/app/reports" element={<p>Reports destination</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const item = await screen.findByRole('article', {
      name: /council approves mosque extension/i,
    });
    const link = within(item).getByRole('link', { name: 'Prepare a report' });
    expect(link).toHaveAttribute('href', '/app/reports?platform=youtube&item=itm_7fb2c9');

    await user.click(link);

    expect(screen.getByText('Reports destination')).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Review queue' })).toBeNull();
  });
});
