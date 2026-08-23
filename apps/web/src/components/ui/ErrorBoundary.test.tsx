import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from './ErrorBoundary';

function Exploding(): never {
  throw new Error('Collected content failed to render');
}

function Recoverable() {
  const [shouldFail, setShouldFail] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setShouldFail(false)}>
        Resolve cause
      </button>
      <ErrorBoundary regionLabel="Signals">
        {shouldFail ? <Exploding /> : <p>Signals loaded</p>}
      </ErrorBoundary>
    </>
  );
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // React logs caught render errors to console.error regardless of the
    // boundary. Silencing keeps the expected failures out of test output.
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders its children when nothing throws', () => {
    render(
      <ErrorBoundary regionLabel="Overview">
        <p>Daily likely-hate rate</p>
      </ErrorBoundary>,
    );

    expect(screen.getByText('Daily likely-hate rate')).toBeInTheDocument();
  });

  it('names the failed region so the reader knows what broke', () => {
    render(
      <ErrorBoundary regionLabel="Trend chart">
        <Exploding />
      </ErrorBoundary>,
    );

    expect(
      screen.getByRole('heading', { name: /trend chart could not be displayed/i }),
    ).toBeInTheDocument();
  });

  it('never exposes the underlying error message to the reader', () => {
    render(
      <ErrorBoundary regionLabel="Explorer">
        <Exploding />
      </ErrorBoundary>,
    );

    expect(screen.queryByText(/Collected content failed to render/)).not.toBeInTheDocument();
  });

  it('exposes the fallback as an alert', () => {
    render(
      <ErrorBoundary regionLabel="Explorer">
        <Exploding />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('restores the subtree when the reader retries after the cause is resolved', async () => {
    const user = userEvent.setup();

    render(<Recoverable />);
    expect(screen.getByRole('alert')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Resolve cause' }));
    await user.click(screen.getByRole('button', { name: 'Try again' }));

    expect(screen.getByText('Signals loaded')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
