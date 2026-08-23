import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ThemeProvider } from '@/app/ThemeProvider';

import {
  clearTourCompletion,
  readTourCompletion,
  writeTourCompletion,
} from '@/features/tour/tour-storage';

import { endFixtureSession, readFixtureSession } from './session';
import { SignUpPage } from './SignUpPage';

vi.mock('@/components/ui/AppLoadingScreen', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui/AppLoadingScreen')>();
  return {
    ...actual,
    entryHoldMs: () => 0,
  };
});

afterEach(() => {
  endFixtureSession();
  clearTourCompletion();
  document.documentElement.removeAttribute('data-theme');
  localStorage.removeItem('amanah.theme');
});

function renderSignUp() {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={['/signup']}>
        <Routes>
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/app" element={<p>Overview</p>} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe('SignUpPage', () => {
  it('says sign-up is open for the MVP and production needs approval', () => {
    renderSignUp();

    expect(screen.getByRole('heading', { name: /^sign up$/i })).toBeVisible();
    expect(screen.getByText(/sign-up is open for this mvp/i)).toBeVisible();
    expect(screen.getByText(/will need approval/i)).toBeVisible();
    expect(screen.queryByText(/invite-only/i)).toBeNull();
    expect(screen.queryByText(/does not create an account/i)).toBeNull();
    expect(screen.queryByText(/synthetic fixture/i)).toBeNull();
  });

  it('reports every missing field at once', async () => {
    const user = userEvent.setup();
    renderSignUp();

    await user.click(screen.getByRole('button', { name: /^sign up$/i }));

    expect(screen.getByText(/enter the name you want shown/i)).toBeVisible();
    expect(screen.getByText(/including the part after the @ sign/i)).toBeVisible();
    expect(screen.getByText(/use at least 8 characters/i)).toBeVisible();
    expect(readFixtureSession()).toBeNull();
  });

  it('carries the display name into the session', async () => {
    const user = userEvent.setup();
    renderSignUp();

    await user.type(screen.getByLabelText(/display name/i), 'Amina R.');
    await user.type(screen.getByLabelText(/email address/i), 'amina@example.org');
    await user.type(screen.getByLabelText(/password/i), 'long-enough-password');
    await user.click(screen.getByRole('button', { name: /^sign up$/i }));

    expect(readFixtureSession()?.displayName).toBe('Amina R.');
    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeVisible();
    });
  });

  it('clears a finished tour so the first signup sees it again', async () => {
    const user = userEvent.setup();
    writeTourCompletion('done');
    renderSignUp();

    await user.type(screen.getByLabelText(/display name/i), 'Amina R.');
    await user.type(screen.getByLabelText(/email address/i), 'amina@example.org');
    await user.type(screen.getByLabelText(/password/i), 'long-enough-password');
    await user.click(screen.getByRole('button', { name: /^sign up$/i }));

    expect(readTourCompletion()).toBeNull();
  });
});
