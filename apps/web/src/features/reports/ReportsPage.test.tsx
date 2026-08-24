import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ReportsPage } from './ReportsPage';

function renderReports(path = '/app/reports') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <ReportsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ReportsPage', () => {
  it('names the view in a single top-level heading', () => {
    renderReports();

    expect(screen.getByRole('heading', { level: 1, name: 'Reports' })).toBeVisible();
  });

  it('shows upload, platform, and generate draft as the primary reporting flow', () => {
    renderReports();

    expect(screen.getByRole('heading', { name: 'Prepare a platform report' })).toBeVisible();
    expect(screen.getByText('Drop a screenshot here')).toBeVisible();
    expect(screen.getByLabelText('Screenshot')).toBeVisible();
    expect(screen.getByLabelText('Report platform')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Generate draft' })).toBeEnabled();
    expect(screen.getByText(/does not notify a government authority/i)).toBeVisible();
  });

  it('shows official YouTube policy and report pages before a draft exists', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.selectOptions(screen.getByLabelText('Report platform'), 'youtube');

    expect(
      screen.getByRole('link', { name: /YouTube hate speech policy \(opens in a new tab\)/i }),
    ).toHaveAttribute('href', 'https://support.google.com/youtube/answer/2801939');
    expect(
      screen.getByRole('link', { name: /YouTube reporting help \(opens in a new tab\)/i }),
    ).toHaveAttribute('href', 'https://support.google.com/youtube/answer/2802027');
    expect(screen.getByText(/does not publish a public mailbox/i)).toBeVisible();
    expect(screen.queryByLabelText('To')).not.toBeInTheDocument();
  });

  it('shows the official Reddit report form and content policy before a draft exists', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.selectOptions(screen.getByLabelText('Report platform'), 'reddit');

    expect(
      screen.getByRole('link', { name: /Reddit Rules \(content policy\) \(opens in a new tab\)/i }),
    ).toHaveAttribute('href', 'https://www.redditinc.com/policies/content-policy');
    expect(
      screen.getByRole('link', { name: /Reddit official report form \(opens in a new tab\)/i }),
    ).toHaveAttribute('href', 'https://www.reddit.com/report');
    expect(
      screen.getByText(/Do not send an ordinary content report to Reddit Legal/i),
    ).toBeVisible();
  });

  it('prepares a YouTube draft with a placeholder addressee and says it was not sent', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.selectOptions(screen.getByLabelText('Report platform'), 'youtube');
    await user.click(screen.getByRole('button', { name: 'Generate draft' }));

    expect(await screen.findByLabelText('Wording to paste')).toBeVisible();
    expect(screen.queryByLabelText('To')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Subject')).not.toBeInTheDocument();
    expect(screen.getByText('Prepared, not sent')).toBeVisible();
    expect((screen.getByLabelText('Wording to paste') as HTMLTextAreaElement).value).toMatch(
      /has not sent it/i,
    );
    expect((screen.getByLabelText('Wording to paste') as HTMLTextAreaElement).value).toContain(
      "They don't belong here. There are other places they can go.",
    );
    expect((screen.getByLabelText('Wording to paste') as HTMLTextAreaElement).value).not.toMatch(
      /\[Redacted/i,
    );
  });

  it('puts the reporter note in the draft as written', async () => {
    const user = userEvent.setup();
    renderReports();
    const note = "They don't belong here. Bloody go somewhere else.";

    await user.selectOptions(screen.getByLabelText('Report platform'), 'reddit');
    await user.type(screen.getByLabelText('What you saw (optional)'), note);
    await user.click(screen.getByRole('button', { name: 'Generate draft' }));

    expect(await screen.findByLabelText('Wording to paste')).toBeVisible();
    expect((screen.getByLabelText('Wording to paste') as HTMLTextAreaElement).value).toContain(
      note,
    );
  });

  it('offers copy and a text download, not a mail app or a submit-to-platform control', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.selectOptions(screen.getByLabelText('Report platform'), 'youtube');
    await user.click(screen.getByRole('button', { name: 'Generate draft' }));
    await screen.findByText('Prepared, not sent');

    expect(screen.getByRole('button', { name: 'Copy wording' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Download .txt' })).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Open in email app' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Download .eml' })).toBeNull();
    expect(screen.queryByRole('button', { name: /submit to/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /submit to youtube/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /^send$/i })).toBeNull();
  });

  it('shows an uploaded screenshot by default with a per-image hide control (PA-01)', async () => {
    const user = userEvent.setup();
    renderReports();
    const file = new File([new Uint8Array(32)], 'capture.png', { type: 'image/png' });

    await user.upload(screen.getByLabelText('Screenshot'), file);

    const toggle = screen.getByRole('button', { name: 'Hide screenshot' });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('img', { name: /capture\.png/i })).toBeVisible();

    await user.click(toggle);

    expect(screen.getByRole('button', { name: 'Show screenshot' })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });

  it('classifies an upload from filename and size, then shows a likely label', async () => {
    const user = userEvent.setup();
    renderReports();
    const file = new File([new Uint8Array(32)], 'capture.png', { type: 'image/png' });

    await user.upload(screen.getByLabelText('Screenshot'), file);

    expect(await screen.findByRole('heading', { name: 'Image classification' })).toBeVisible();
    expect(screen.getByText('Classified as likely anti-Muslim hate')).toBeVisible();
    expect(screen.getByText(/did not read pixels/i)).toBeVisible();
  });

  it('does not host the research image catalog', () => {
    renderReports();

    expect(screen.queryByRole('heading', { name: 'Research image examples' })).toBeNull();
  });

  it('reads platform and item from the review query without fetching the item', () => {
    renderReports('/app/reports?platform=reddit&item=itm_3ad014');

    expect(screen.getByLabelText('Report platform')).toHaveValue('reddit');
    expect(screen.getByText(/itm_3ad014/)).toBeVisible();
    expect(screen.getByText(/content reference, not a person/i)).toBeVisible();
  });

  it('states the scope a report would freeze, read from the address bar', () => {
    renderReports('/app/reports?from=2026-08-09&to=2026-08-22&platform=youtube');

    expect(screen.getByRole('heading', { name: 'Research report' })).toBeVisible();
    expect(screen.getByText('2026-08-09 to 2026-08-22')).toBeVisible();
    expect(screen.getByText('youtube')).toBeVisible();
  });

  it('says a hate-type selection is not carried into the snapshot', () => {
    renderReports('/app/reports?hate_type=collective_blame');

    expect(
      screen.getByText(/hate-type selection is active on screen but is not carried/i),
    ).toBeVisible();
  });

  it('offers generation once a title is typed, and exports only after freezing', async () => {
    const user = userEvent.setup();
    renderReports();

    // Exports do not exist before there is a snapshot to export.
    expect(screen.queryByRole('button', { name: 'Download aggregate CSV' })).toBeNull();

    await user.type(screen.getByLabelText('Report title'), 'August monitored sample');
    await user.click(screen.getByRole('button', { name: 'Generate report' }));

    expect(await screen.findByText('August monitored sample')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Download aggregate CSV' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Print or save as PDF' })).toBeEnabled();
  });

  it('freezes figures with their denominators and says they will not change', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.type(screen.getByLabelText('Report title'), 'August monitored sample');
    await user.click(screen.getByRole('button', { name: 'Generate report' }));

    expect(await screen.findByText('Muslim-related items')).toBeVisible();
    expect(screen.getByText('Likely hate rate')).toBeVisible();
    expect(screen.getByText(/do not change when the data behind them does/i)).toBeVisible();
    expect(screen.getByText(/not a prevalence estimate for any platform/i)).toBeVisible();
  });

  it('states that CSV carries aggregates only and that item-level export is gated', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.type(screen.getByLabelText('Report title'), 'August monitored sample');
    await user.click(screen.getByRole('button', { name: 'Generate report' }));

    const note = await screen.findByText(/carries counts and denominators only/i);
    expect(note).toHaveTextContent(/item-level export needs elevated permission/i);
  });

  it('lists what the report will contain, including its limitations', () => {
    renderReports();

    expect(screen.getByText('Coverage and denominators')).toBeVisible();
    expect(screen.getByText('Model disclosure')).toBeVisible();
    expect(screen.getByText('Limitations')).toBeVisible();
  });
});
