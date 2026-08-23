import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PATH_CYCLE_MS, PathVisuals, ROOM_SLIDES } from './PathVisuals';

function mockMatchMedia(prefersReducedMotion: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: query.includes('prefers-reduced-motion: reduce') ? prefersReducedMotion : false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

function restoreMatchMedia(): void {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => {
  vi.useRealTimers();
  restoreMatchMedia();
});

describe('PathVisuals', () => {
  it('shows several room stills and keeps the model on its own tab', () => {
    render(<PathVisuals />);

    const carousel = screen.getByRole('region', { name: 'The room online' });
    expect(carousel).toHaveAttribute('aria-roledescription', 'carousel');
    expect(within(carousel).getByText('Isolation')).toBeVisible();
    expect(within(carousel).getByText(/the face is not visible/i)).toBeVisible();
    expect(within(carousel).getByRole('img')).toHaveAccessibleName(/the face is not visible/i);

    const dots = screen.getByRole('group', { name: 'Choose a still' });
    expect(within(dots).getAllByRole('button')).toHaveLength(ROOM_SLIDES.length);
    expect(screen.getByRole('tab', { name: 'The room' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'The model' })).toHaveAttribute(
      'aria-selected',
      'false',
    );
    expect(screen.queryByRole('button', { name: /grievance/i })).toBeNull();
  });

  it('advances stills on the path-cycle interval', () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    render(<PathVisuals />);

    expect(screen.getByText('Isolation')).toBeVisible();

    act(() => {
      vi.advanceTimersByTime(PATH_CYCLE_MS);
    });

    expect(screen.getByText('An empty chair')).toBeVisible();
    expect(screen.queryByText('Isolation')).toBeNull();
  });

  it('does not autoplay when reduced motion is preferred', () => {
    mockMatchMedia(true);
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    render(<PathVisuals />);

    expect(screen.getByText('Isolation')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Pause' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Play' })).toBeNull();

    act(() => {
      vi.advanceTimersByTime(PATH_CYCLE_MS * 2);
    });

    expect(screen.getByText('Isolation')).toBeVisible();
    expect(screen.queryByText('An empty chair')).toBeNull();
  });

  it('stops autoplay when Pause is pressed and resumes on Play', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const user = userEvent.setup();
    render(<PathVisuals />);

    await user.click(screen.getByRole('button', { name: 'Pause' }));
    expect(screen.getByRole('button', { name: 'Play' })).toBeVisible();

    act(() => {
      vi.advanceTimersByTime(PATH_CYCLE_MS * 2);
    });

    expect(screen.getByText('Isolation')).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Play' }));
    expect(screen.getByRole('button', { name: 'Pause' })).toBeVisible();
    await user.unhover(screen.getByRole('region', { name: 'The room online' }));

    act(() => {
      vi.advanceTimersByTime(PATH_CYCLE_MS);
    });

    expect(screen.getByText('An empty chair')).toBeVisible();
  });

  it('pauses autoplay while the carousel is hovered', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const user = userEvent.setup();
    render(<PathVisuals />);

    await user.hover(screen.getByRole('region', { name: 'The room online' }));

    act(() => {
      vi.advanceTimersByTime(PATH_CYCLE_MS * 2);
    });

    expect(screen.getByText('Isolation')).toBeVisible();
    expect(screen.queryByText('An empty chair')).toBeNull();
  });

  it('moves to a chosen still with the next control and a dot', async () => {
    const user = userEvent.setup();
    render(<PathVisuals />);

    await user.click(screen.getByRole('button', { name: 'Next still' }));
    expect(screen.getByText('An empty chair')).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'The wall that moves on' }));
    expect(screen.getByText('Comments stack and scroll. No one stays to answer.')).toBeVisible();
    expect(screen.getByRole('button', { name: 'The wall that moves on' })).toHaveAttribute(
      'aria-current',
      'true',
    );
  });

  it('does not auto-advance Borum stages when the model tab is selected', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const user = userEvent.setup();
    render(<PathVisuals />);

    await user.click(screen.getByRole('tab', { name: 'The model' }));

    expect(screen.getByRole('button', { name: /grievance/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.queryByRole('region', { name: 'The room online' })).toBeNull();

    act(() => {
      vi.advanceTimersByTime(PATH_CYCLE_MS * 3);
    });

    expect(screen.getByRole('button', { name: /grievance/i })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: /injustice/i })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });
});
