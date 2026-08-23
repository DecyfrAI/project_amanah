import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { resetFixtureProvider } from '@/api/fixture-provider';
import {
  endFixtureSession,
  readFixtureSession,
  startFixtureSession,
} from '@/features/auth/session';

import { ProfilePage } from './ProfilePage';

afterEach(() => {
  endFixtureSession();
});

function renderProfile() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfilePage', () => {
  beforeEach(() => {
    resetFixtureProvider();
    startFixtureSession('Amina R.', 'amina@example.org');
  });

  it('shows the current name and email', () => {
    renderProfile();

    expect(screen.getByLabelText(/display name/i)).toHaveValue('Amina R.');
    expect(screen.getByLabelText(/email address/i)).toHaveValue('amina@example.org');
  });

  it('shows initials when there is no picture', () => {
    renderProfile();

    expect(screen.getByText('AR')).toBeVisible();
  });

  it('saves a new display name into the session', async () => {
    const user = userEvent.setup();
    renderProfile();

    const name = screen.getByLabelText(/display name/i);
    await user.clear(name);
    await user.type(name, 'Yusuf K.');
    await user.click(screen.getByRole('button', { name: /save details/i }));

    expect(readFixtureSession()?.displayName).toBe('Yusuf K.');
    expect(screen.getByText(/profile updated for this session/i)).toBeVisible();
  });

  it('refuses an empty display name', async () => {
    const user = userEvent.setup();
    renderProfile();

    await user.clear(screen.getByLabelText(/display name/i));
    await user.click(screen.getByRole('button', { name: /save details/i }));

    expect(screen.getByText(/enter a display name/i)).toBeVisible();
    expect(readFixtureSession()?.displayName).toBe('Amina R.');
  });

  it('refuses a malformed email', async () => {
    const user = userEvent.setup();
    renderProfile();

    const email = screen.getByLabelText(/email address/i);
    await user.clear(email);
    await user.type(email, 'not-an-address');
    await user.click(screen.getByRole('button', { name: /save details/i }));

    expect(screen.getByText(/including the part after the @ sign/i)).toBeVisible();
    expect(readFixtureSession()?.email).toBe('amina@example.org');
  });

  it('says plainly that no password exists to change yet', () => {
    renderProfile();

    expect(screen.getByRole('heading', { name: /^password$/i })).toBeVisible();
    expect(screen.getByText(/there is no password to change yet/i)).toBeVisible();
    expect(screen.queryByLabelText(/new password/i)).toBeNull();
  });

  it('lists notes the signed-in viewer left on insights', async () => {
    renderProfile();

    expect(await screen.findByRole('heading', { name: /your notes/i })).toBeVisible();
    expect(screen.getByText(/keeping this window open/i)).toBeVisible();
    expect(
      screen.getByRole('link', {
        name: /collective-blame share rose in the monitored youtube sample/i,
      }),
    ).toHaveAttribute('href', '/app/insights/ins_collective_blame');
  });
});
