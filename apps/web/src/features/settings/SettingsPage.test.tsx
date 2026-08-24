import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';

import { MediaPreferenceProvider } from './media-preference';
import { SettingsPage } from './SettingsPage';

/**
 * Settings reads and writes the media preference through the profile API, so
 * the page needs both the query client and the preference provider — the same
 * pair `AppShell` mounts around every authenticated route.
 */
function renderSettings() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MediaPreferenceProvider>
        <SettingsPage />
      </MediaPreferenceProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  sessionStorage.clear();
  resetFixtureProvider();
});

describe('SettingsPage', () => {
  it('names the view in a single top-level heading', () => {
    renderSettings();

    expect(screen.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible();
  });

  it('groups the safety controls under a legend', () => {
    renderSettings();

    expect(screen.getByRole('group', { name: 'What you see by default' })).toBeVisible();
    expect(screen.getByRole('group', { name: 'Row height in research tables' })).toBeVisible();
  });

  it('starts with media visible and does not offer text redaction (PA-01)', async () => {
    renderSettings();

    const blur = screen.getByRole('checkbox', { name: 'Blur media by default' });
    await waitFor(() => {
      expect(blur).not.toBeChecked();
    });
    expect(screen.getByText(/Media appears without blurring/i)).toBeVisible();
    expect(screen.queryByRole('checkbox', { name: /redact slurs/i })).toBeNull();
    expect(screen.getByText(/comment wording is shown in full/i)).toBeVisible();
  });

  it('opting in to blur is reflected in the summary and saved to the profile', async () => {
    const user = userEvent.setup();
    renderSettings();

    await user.click(screen.getByRole('checkbox', { name: 'Blur media by default' }));

    await waitFor(() => {
      expect(screen.getByText(/Media stays blurred until you show it/i)).toBeVisible();
    });
    expect(screen.getByRole('checkbox', { name: 'Blur media by default' })).toBeChecked();
  });

  it('says the media preference is saved while density is not', () => {
    renderSettings();

    expect(screen.getAllByText(/saved to your profile/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/not saved between visits/i)).toBeVisible();
  });

  it('starts at comfortable density and changes the sample table when compact is chosen', async () => {
    const user = userEvent.setup();
    renderSettings();

    const comfortable = screen.getByRole('radio', { name: 'Comfortable' });
    const compact = screen.getByRole('radio', { name: 'Compact' });
    expect(comfortable).toBeChecked();

    const before = screen.getByRole('table').className;
    await user.click(compact);

    expect(compact).toBeChecked();
    expect(comfortable).not.toBeChecked();
    expect(screen.getByRole('table').className).not.toBe(before);
  });

  it('shows the model score as a score rather than as a proportion', () => {
    renderSettings();

    const row = screen.getByRole('row', { name: /itm_7fb2c9/ });
    expect(row).toHaveTextContent('0.58');
    expect(row).not.toHaveTextContent('%');
  });

  it('points at the sidebar for the theme rather than repeating the control', () => {
    renderSettings();

    expect(screen.getByRole('heading', { level: 2, name: 'Theme' })).toBeVisible();
    expect(screen.getByText(/toggle lives at the foot of the sidebar/i)).toBeVisible();
    expect(screen.queryByRole('radio', { name: /dark/i })).toBeNull();
  });
});
