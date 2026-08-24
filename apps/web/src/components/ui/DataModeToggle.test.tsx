import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { clearMockDataPreference, readSelectedDataMode, selectApiDataMode } from '@/api';
import { DataModeProvider, useDataMode } from '@/app/DataModeProvider';

import { DataModeToggle } from './DataModeToggle';

function DataModeProbe() {
  const { mode } = useDataMode();
  return <output aria-label="Selected data mode">{mode}</output>;
}

function withProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <DataModeProvider>{ui}</DataModeProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.stubEnv('VITE_DATA_MODE', 'live');
  clearMockDataPreference();
  selectApiDataMode('live');
});

afterEach(() => {
  clearMockDataPreference();
  vi.unstubAllEnvs();
  selectApiDataMode(readSelectedDataMode());
});

describe('DataModeToggle', () => {
  it('switches between the configured provider and mock data', async () => {
    const user = userEvent.setup();
    render(
      withProviders(
        <>
          <DataModeToggle />
          <DataModeProbe />
        </>,
      ),
    );

    const toggle = screen.getByRole('switch', { name: 'Mock data' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(screen.getByRole('status', { name: 'Selected data mode' })).toHaveTextContent('live');

    await user.click(toggle);

    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    expect(screen.getByRole('status', { name: 'Selected data mode' })).toHaveTextContent('fixture');

    await user.click(toggle);

    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));
    expect(screen.getByRole('status', { name: 'Selected data mode' })).toHaveTextContent('live');
  });

  it('keeps mock data on when the build has no live mode', () => {
    vi.stubEnv('VITE_DATA_MODE', 'fixture');
    selectApiDataMode('fixture');

    render(withProviders(<DataModeToggle />));

    const toggle = screen.getByRole('switch', { name: 'Mock data' });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    expect(toggle).toBeDisabled();
  });
});
