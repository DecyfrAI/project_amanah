import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';

import { ThemeProvider } from '@/app/ThemeProvider';

import { endFixtureSession, hasFixtureSession } from './session';
import { LoginPage } from './LoginPage';
import { SessionProvider } from './SessionProvider';

afterEach(() => {
  endFixtureSession();
  document.documentElement.removeAttribute('data-theme');
  localStorage.removeItem('amanah.theme');
});

function renderLogin() {
  return render(
    <SessionProvider>
      <ThemeProvider>
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/app" element={<p>Overview</p>} />
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </SessionProvider>,
  );
}

describe('LoginPage', () => {
  it('says sign-up is open for the MVP and production needs approval', () => {
    renderLogin();

    expect(screen.getByRole('heading', { name: /log in to the workspace/i })).toBeVisible();
    expect(screen.getByText(/sign-up is open for this mvp/i)).toBeVisible();
    expect(screen.getByText(/will need approval/i)).toBeVisible();
    expect(screen.queryByText(/invite-only/i)).toBeNull();
    expect(screen.getByRole('link', { name: /^sign up$/i })).toHaveAttribute('href', '/signup');
    expect(screen.getByText(/no account yet/i)).toBeVisible();
    expect(screen.queryByText(/no live accounts/i)).toBeNull();
    expect(screen.queryByText(/synthetic fixture/i)).toBeNull();
  });

  it('reports a malformed email without starting a session', async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email address/i), 'not-an-address');
    await user.type(screen.getByLabelText(/password/i), 'whichever');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(screen.getByText(/including the part after the @ sign/i)).toBeVisible();
    expect(screen.getByLabelText(/email address/i)).toHaveAttribute('aria-invalid', 'true');
    expect(hasFixtureSession()).toBe(false);
  });

  it('requires a password', async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email address/i), 'reviewer@example.org');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(screen.getByText(/enter your password/i)).toBeVisible();
    expect(hasFixtureSession()).toBe(false);
  });

  it('opens the workspace once both fields are filled', async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/email address/i), 'reviewer@example.org');
    await user.type(screen.getByLabelText(/password/i), 'fixture-session');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(hasFixtureSession()).toBe(true);
    await waitFor(() => {
      expect(screen.getByText('Overview')).toBeVisible();
    });
  });
});
