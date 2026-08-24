import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DataModeProvider } from '@/app/DataModeProvider';

import { FixtureBanner } from './FixtureBanner';

describe('FixtureBanner', () => {
  it('states that the figures are synthetic in fixture mode', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DataModeProvider>
          <FixtureBanner />
        </DataModeProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('status')).toHaveTextContent(/these figures are synthetic/i);
  });
});
