import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';
import { InsightPage } from '@/features/insights/InsightPage';

import { OverviewPage } from './OverviewPage';

beforeEach(() => {
  resetFixtureProvider();
});

function renderOverview(search = '/app') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[search]}>
        <Routes>
          <Route path="/app" element={<OverviewPage />} />
          <Route path="/app/insights/:insightId" element={<InsightPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('OverviewPage', () => {
  it('shows coinciding news as outbound context, not a classification', async () => {
    renderOverview();

    const section = await screen.findByRole('region', { name: /in the news/i });
    const link = await within(section).findByRole('link', {
      name: /commons hears questions on mosque safety after vandalism in a northern city \(opens article on BBC News\)/i,
    });

    expect(link).toHaveAttribute(
      'href',
      'https://www.bbc.co.uk/news/uk-politics-2026-08-15-mosque-safety-commons',
    );
    expect(within(section).queryByText(/classified as likely hate/i)).toBeNull();
  });

  it('states the coverage the figures rest on', async () => {
    renderOverview();
    const strip = await screen.findByRole('region', { name: /what this view covers/i });

    expect(within(strip).getByText('2026-07-18 to 2026-08-16 (UTC)')).toBeVisible();
    expect(within(strip).getByText('36 videos and threads')).toBeVisible();
    expect(within(strip).getByText('5,491')).toBeVisible();
  });

  it('warns that a collection day failed rather than hiding it', async () => {
    renderOverview();

    expect(await screen.findByText(/coverage warning/i)).toBeVisible();
    expect(screen.getByText(/collection failed on 2026-08-07/i)).toBeVisible();
    expect(screen.getByText(/not a measurement of a whole platform/i)).toBeVisible();
  });

  it('shows the likely hate rate with its numerator and denominator', async () => {
    renderOverview();
    const card = await screen.findByRole('article', { name: /likely hate rate/i });

    expect(within(card).getByText('18.7%')).toBeVisible();
    expect(within(card).getByText('253 of 1,350')).toBeVisible();
    expect(
      within(card).getByText(/up 1.4 percentage points against the previous 30 days/i),
    ).toBeVisible();
    expect(
      within(card).getByRole('link', { name: /open likely hate rate in explorer/i }),
    ).toHaveAttribute('href', '/app/explorer');
  });

  it('opens a review figure in Explorer with that review state selected', async () => {
    renderOverview();
    const card = await screen.findByRole('article', { name: /confirmed by review/i });

    expect(
      within(card).getByRole('link', { name: /open confirmed by review in explorer/i }),
    ).toHaveAttribute('href', '/app/explorer?review_state=confirmed');
  });

  it('marks a model-only figure as unreviewed', async () => {
    renderOverview();
    const card = await screen.findByRole('article', { name: /classified as likely hate/i });

    expect(within(card).getByText(/model classification, not yet reviewed/i)).toBeVisible();
  });

  it('keeps confirmed review counts separate from the model count', async () => {
    renderOverview();
    const confirmed = await screen.findByRole('article', { name: /confirmed by review/i });

    expect(within(confirmed).getByText('115 of 121')).toBeVisible();
    expect(within(confirmed).queryByText(/model classification/i)).toBeNull();
  });

  it('describes the collection gap in the chart summary', async () => {
    renderOverview();

    expect(await screen.findByText(/29 of 30 days were collected/i)).toBeVisible();
    expect(
      screen.getByText(/7 august is drawn as a break in the line rather than as zero/i),
    ).toBeVisible();
  });

  it('reads out a selected day with its counts', async () => {
    const user = userEvent.setup();
    renderOverview();
    const button = await screen.findByRole('button', { name: /^16 august/i });

    await user.click(button);

    expect(
      screen.getByText(/16 august: 6 of 31 muslim-related items classified as likely hate, 19.4%/i),
    ).toBeVisible();
  });

  it('refuses to state a rate for the uncollected day', async () => {
    const user = userEvent.setup();
    renderOverview();
    const button = await screen.findByRole('button', { name: /7 august, no collection/i });

    await user.click(button);

    expect(screen.getByText(/collection failed, so no rate can be stated/i)).toBeVisible();
    expect(screen.queryByRole('link', { name: /view supporting records/i })).toBeNull();
  });

  it('offers a scoped drill-down into the Explorer for a collected day', async () => {
    const user = userEvent.setup();
    renderOverview();

    await user.click(await screen.findByRole('button', { name: /^15 august/i }));

    expect(
      screen.getByRole('link', { name: /view supporting records for 15 august/i }),
    ).toHaveAttribute('href', '/app/explorer?from=2026-08-15&to=2026-08-15');
  });

  it('lets a rate-chart point open Explorer on that day', async () => {
    renderOverview();

    expect(
      await screen.findByRole('link', { name: 'Open Explorer for 16 August' }),
    ).toHaveAttribute('href', '/app/explorer?from=2026-08-16&to=2026-08-16');
  });

  it('offers the chart as a table, with the gap day named', async () => {
    const user = userEvent.setup();
    renderOverview();

    await user.click(await screen.findByText(/show these numbers as a table/i));

    const table = screen.getByRole('table', { name: /daily likely anti-muslim hate rate/i });
    const gapRow = within(table).getByRole('row', { name: /7 august no collection on this day/i });

    expect(gapRow).toBeVisible();
    expect(within(table).getByRole('row', { name: /1 August.*43 7 16\.3%/i })).toBeVisible();
  });

  it('narrows the figures when a platform filter is in the URL', async () => {
    renderOverview('/app?platform=youtube&from=2026-08-01&to=2026-08-16');

    const strip = await screen.findByRole('region', { name: /what this view covers/i });
    expect(within(strip).getByText('22 videos')).toBeVisible();
    expect(within(strip).getByText('1,798')).toBeVisible();

    const rate = screen.getByRole('article', { name: /likely hate rate/i });
    expect(within(rate).getByText('22.3%')).toBeVisible();
    expect(within(rate).getByText('87 of 390')).toBeVisible();
  });

  it('switches the time series to volumes', async () => {
    const user = userEvent.setup();
    renderOverview();

    await user.click(await screen.findByRole('button', { name: /volume over time/i }));

    expect(
      screen.getByText(/likely-hate items collected each day, stacked by source/i),
    ).toBeVisible();
    expect(screen.getByText(/253 items classified as likely anti-Muslim hate/i)).toBeVisible();
  });

  it('shows the source stack under the rate series', async () => {
    renderOverview();

    expect(
      await screen.findByText(/likely-hate items collected each day, stacked by source/i),
    ).toBeVisible();
    expect(screen.getByText(/stacked largest to smallest: YouTube, Reddit/i)).toBeVisible();
  });

  it('lets a breakdown row drill into the Explorer with that slice selected', async () => {
    renderOverview();

    const threat = await screen.findByRole('link', { name: 'Threat or incitement' });
    expect(threat).toHaveAttribute('href', '/app/explorer?hate_type=threat');
  });

  it('starts a snapshot insight from a collected day', async () => {
    const user = userEvent.setup();
    renderOverview();

    await user.click(await screen.findByRole('button', { name: /^16 august/i }));
    await user.click(screen.getByRole('button', { name: /start an insight on 16 august/i }));

    expect(
      await screen.findByRole('heading', { name: /likely-hate rate on 16 august/i }),
    ).toBeVisible();
    expect(screen.getAllByText(/6 of 31/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/snapshot started from a figure/i)).toBeVisible();
    expect(await screen.findByRole('heading', { name: 'Discussion' })).toBeVisible();
  });
});
