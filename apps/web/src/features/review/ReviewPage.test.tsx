import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ReviewPage } from './ReviewPage';

function renderReview() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ReviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function firstQueueItem(): HTMLElement {
  return screen.getByRole('article', { name: /council approves mosque extension/i });
}

describe('ReviewPage', () => {
  it('names the view in a single top-level heading', () => {
    renderReview();

    expect(screen.getByRole('heading', { level: 1, name: 'Review queue' })).toBeVisible();
  });

  it('says that a decision appends beside the prediction rather than replacing it', () => {
    renderReview();

    expect(screen.getByText(/never overwrites it/i)).toBeVisible();
  });

  it('shows the queue figures with their denominators', () => {
    renderReview();

    expect(screen.getByText('34 of 1,208 classified items in the window')).toBeVisible();
    expect(screen.getByText('41 confirmations of 57 decided items')).toBeVisible();
  });

  it('reports days without collection as a gap rather than as zero', () => {
    renderReview();

    expect(
      screen.getByText(/gap in collection, not three days without anything to find/i),
    ).toBeVisible();
  });

  it('labels the review state in words, not by colour alone', () => {
    renderReview();

    expect(within(firstQueueItem()).getByText('Awaiting review')).toBeVisible();
  });

  it('shows the comment wording on every queue item, with no reveal control', () => {
    renderReview();

    const item = firstQueueItem();
    expect(
      within(item).getByText(/they don't belong here. there are other places they can go/i),
    ).toBeVisible();
    expect(within(item).queryByRole('button', { name: /reveal/i })).toBeNull();
    expect(screen.queryByText(/slur redacted/i)).toBeNull();
    expect(screen.getByText(/those people are not to be believed/i)).toBeVisible();
  });

  it('disables every decision and gives the reason on screen', () => {
    renderReview();

    const item = within(firstQueueItem());
    expect(item.getByRole('button', { name: 'Confirm label' })).toBeDisabled();
    expect(item.getByRole('button', { name: 'Correct label' })).toBeDisabled();
    expect(item.getByRole('button', { name: 'Skip for now' })).toBeDisabled();
    expect(item.getByText(/needs the review API, which is not connected yet/i)).toBeVisible();
  });

  it('presents the model score as a score, with its confidence tier in words', () => {
    renderReview();

    expect(within(firstQueueItem()).getByText('0.58 (low confidence)')).toBeVisible();
  });

  it('says the figures are a mockup rather than a reading', () => {
    renderReview();

    expect(screen.getByText('Design mockup, not a reading')).toBeVisible();
  });

  it('does not host the report-draft form on Review', () => {
    renderReview();

    expect(screen.queryByLabelText('Screenshot')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Generate draft' })).toBeNull();
    expect(screen.queryByLabelText('Report platform')).toBeNull();
    expect(screen.getByLabelText('Research image')).toBeVisible();
    expect(screen.getByText('Drop a research image here')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Save training label' })).toBeDisabled();
  });

  it('shows research examples unblurred by default, each with its own hide control (PA-01)', async () => {
    renderReview();

    expect(await screen.findByRole('heading', { name: 'Research image examples' })).toBeVisible();
    // Images are visible by default now, so every card offers to *hide* rather
    // than to reveal, and reports itself as expanded.
    const toggles = await screen.findAllByRole('button', { name: 'Hide example' });
    expect(toggles.length).toBe(42);
    expect(toggles[0]).toHaveAttribute('aria-expanded', 'true');
  });

  it('routes Prepare a report to Reports instead of opening a form here', async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: 0 } } });
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

    const link = within(firstQueueItem()).getByRole('link', { name: 'Prepare a report' });
    expect(link).toHaveAttribute('href', '/app/reports?platform=youtube&item=itm_7fb2c9');

    await user.click(link);

    expect(screen.getByText('Reports destination')).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Review queue' })).toBeNull();
  });
});
