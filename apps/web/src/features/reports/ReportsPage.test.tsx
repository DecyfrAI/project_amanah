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

  it('offers a working research-report form rather than inert scope controls', () => {
    renderReports();

    expect(screen.getByRole('heading', { name: 'Research report' })).toBeVisible();
    expect(screen.getByLabelText('Report title')).toBeEnabled();
    expect(screen.getByLabelText('Include an aggregate CSV')).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Generate report' })).toBeEnabled();
  });

  it('refuses to create a snapshot without a usable title', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.click(screen.getByRole('button', { name: 'Generate report' }));

    expect(screen.getByText(/at least three characters/i)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Download aggregate CSV' })).toBeNull();
  });

  it('creates a real snapshot and shows its scope, figures, and limitations', async () => {
    const user = userEvent.setup();
    renderReports();

    await user.type(screen.getByLabelText('Report title'), 'Two-week coverage');
    await user.click(screen.getByRole('button', { name: 'Generate report' }));

    expect(
      await screen.findByRole('heading', { level: 3, name: 'Two-week coverage' }),
    ).toBeVisible();
    // The snapshot states what it does and does not support, beside the figures.
    expect(screen.getByText(/never platform-wide prevalence/i)).toBeVisible();
    expect(screen.getByText('Methodology version')).toBeVisible();
  });

  it('enables CSV download and print only once a snapshot exists', async () => {
    const user = userEvent.setup();
    renderReports();

    expect(screen.queryByRole('button', { name: 'Print or save as PDF' })).toBeNull();

    await user.type(screen.getByLabelText('Report title'), 'Two-week coverage');
    await user.click(screen.getByRole('button', { name: 'Generate report' }));

    expect(await screen.findByRole('button', { name: 'Download aggregate CSV' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Print or save as PDF' })).toBeEnabled();
  });

  it('states that the export carries aggregates only', () => {
    renderReports();

    expect(screen.getByText(/Aggregate counts and denominators only/i)).toBeVisible();
  });

  it('lists what the report will contain, including its limitations', () => {
    renderReports();

    expect(screen.getByText('Coverage and denominators')).toBeVisible();
    expect(screen.getByText('Model disclosure')).toBeVisible();
    expect(screen.getByText('Limitations')).toBeVisible();
  });
});
