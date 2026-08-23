import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { readTourCompletion, TOUR_STORAGE_KEY, writeTourCompletion } from './tour-storage';
import { TOUR_STEPS } from './tour-steps';
import { WorkspaceTour } from './WorkspaceTour';

function LocationReadout() {
  const location = useLocation();
  return <span data-testid="tour-location">{location.pathname}</span>;
}

function renderTour() {
  return render(
    <MemoryRouter initialEntries={['/app']}>
      <LocationReadout />
      <WorkspaceTour />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.removeItem(TOUR_STORAGE_KEY);
});

afterEach(() => {
  localStorage.removeItem(TOUR_STORAGE_KEY);
});

describe('WorkspaceTour', () => {
  it('opens automatically when no completion is stored', async () => {
    renderTour();

    expect(await screen.findByRole('heading', { name: TOUR_STEPS[0]!.title })).toBeVisible();
    expect(screen.getByText(`1 / ${String(TOUR_STEPS.length)}`)).toBeVisible();
  });

  it('stays closed when the tour was already finished', () => {
    writeTourCompletion('done');
    renderTour();

    expect(screen.queryByRole('heading', { name: TOUR_STEPS[0]!.title })).not.toBeInTheDocument();
  });

  it('advances, then finishes and persists completion', async () => {
    const user = userEvent.setup();
    renderTour();

    await screen.findByRole('heading', { name: TOUR_STEPS[0]!.title });
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByRole('heading', { name: TOUR_STEPS[1]!.title })).toBeVisible();

    await TOUR_STEPS.slice(2).reduce(async (ready) => {
      await ready;
      await user.click(screen.getByRole('button', { name: 'Next' }));
    }, Promise.resolve());

    expect(
      screen.getByRole('heading', { name: TOUR_STEPS[TOUR_STEPS.length - 1]!.title }),
    ).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Finish' }));
    expect(readTourCompletion()).toBe('done');
    expect(screen.queryByRole('heading', { name: TOUR_STEPS[0]!.title })).not.toBeInTheDocument();
  });

  it('opens Settings and Profile as their own destinations', async () => {
    const user = userEvent.setup();
    renderTour();

    const settingsIndex = TOUR_STEPS.findIndex((step) => step.id === 'settings');
    const profileIndex = TOUR_STEPS.findIndex((step) => step.id === 'profile');
    expect(settingsIndex).toBeGreaterThan(-1);
    expect(profileIndex).toBeGreaterThan(settingsIndex);

    await screen.findByRole('heading', { name: TOUR_STEPS[0]!.title });
    await TOUR_STEPS.slice(0, settingsIndex).reduce(async (ready) => {
      await ready;
      await user.click(screen.getByRole('button', { name: 'Next' }));
    }, Promise.resolve());
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByTestId('tour-location')).toHaveTextContent('/app/settings');
    });

    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByRole('heading', { name: 'Profile' })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByTestId('tour-location')).toHaveTextContent('/app/profile');
    });
  });

  it('skips and records skipped', async () => {
    const user = userEvent.setup();
    renderTour();

    await screen.findByRole('heading', { name: TOUR_STEPS[0]!.title });
    await user.click(screen.getByRole('button', { name: 'Skip' }));

    expect(readTourCompletion()).toBe('skipped');
  });
});
