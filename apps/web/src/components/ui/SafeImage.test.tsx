import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';
import { MediaPreferenceProvider, useMediaPreference } from '@/features/settings/media-preference';

import { SafeImage } from './SafeImage';

function renderImage(extra?: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MediaPreferenceProvider>
        <SafeImage src="/media/example.png" alt="Harmful research example, poster form." />
        {extra}
      </MediaPreferenceProvider>
    </QueryClientProvider>,
  );
}

/** Flips the stored preference the way the Settings checkbox does. */
function BlurSwitch() {
  const { setBlurMedia, blurMedia } = useMediaPreference();
  return (
    <button type="button" onClick={() => setBlurMedia(!blurMedia)}>
      toggle preference
    </button>
  );
}

afterEach(() => {
  sessionStorage.clear();
  resetFixtureProvider();
});

describe('SafeImage', () => {
  it('shows the image by default and offers to hide it (PA-01)', async () => {
    renderImage();

    const toggle = await screen.findByRole('button', { name: 'Hide image' });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('img', { name: /poster form/i })).toBeVisible();
  });

  it('keeps a per-image override that does not change the stored preference', async () => {
    const user = userEvent.setup();
    renderImage();

    await user.click(await screen.findByRole('button', { name: 'Hide image' }));

    const shown = screen.getByRole('button', { name: 'Show image' });
    expect(shown).toHaveAttribute('aria-expanded', 'false');
    // Still rendered and still reachable: blur is a display treatment, never
    // an access control that removes the element.
    expect(screen.getByRole('img', { name: /poster form/i })).toBeVisible();
  });

  it('applies a preference change to an already-rendered image without a reload', async () => {
    const user = userEvent.setup();
    renderImage(<BlurSwitch />);

    await screen.findByRole('button', { name: 'Hide image' });

    await user.click(screen.getByRole('button', { name: 'toggle preference' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Show image' })).toBeVisible();
    });
  });
});
