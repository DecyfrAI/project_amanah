import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { PlatformReportDraft } from './PlatformReportDraft';

function renderDraft() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PlatformReportDraft />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function pngFile(name = 'capture.png') {
  return new File([new Uint8Array(64)], name, { type: 'image/png' });
}

afterEach(() => {
  resetFixtureProvider();
});

describe('image upload in the report draft (B-S28)', () => {
  it('tells the person what happens to the file before they choose one', () => {
    renderDraft();

    // The old copy claimed the file never left the tab. It does now, so the
    // interface has to say so rather than reassure falsely.
    expect(screen.queryByText(/file stays in this tab/i)).toBeNull();
    expect(screen.getByText(/metadata are removed before storage/i)).toBeVisible();
    expect(screen.getByText(/only you can read it/i)).toBeVisible();
  });

  it('uploads the image and then classifies what was stored', async () => {
    const user = userEvent.setup();
    renderDraft();

    await user.upload(screen.getByLabelText('Screenshot'), pngFile());

    // The confirmation is its own line, distinct from the pre-upload hint.
    expect(await screen.findByText('Stored privately.', { exact: false })).toBeVisible();
    expect(await screen.findByRole('img', { name: /capture\.png/i })).toBeVisible();
  });

  it('does not claim to have stored a file the local check rejected', async () => {
    const user = userEvent.setup();
    renderDraft();

    const notAnImage = new File([new Uint8Array(8)], 'notes.txt', { type: 'text/plain' });
    await user.upload(screen.getByLabelText('Screenshot'), notAnImage);

    expect(screen.queryByText('Stored privately.', { exact: false })).toBeNull();
    expect(screen.queryByRole('img', { name: /notes\.txt/i })).toBeNull();
  });
});
