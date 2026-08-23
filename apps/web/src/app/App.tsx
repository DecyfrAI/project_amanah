import { BrowserRouter } from 'react-router-dom';

import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

import { AppProviders } from './providers';
import { AppRouter } from './router';

/**
 * Application root.
 *
 * Public marketing and login sit outside the guard. Insights and discussion
 * sit behind the invited fixture session until Supabase auth lands in FE-03.
 */
export function App() {
  return (
    <BrowserRouter>
      <AppProviders>
        <ErrorBoundary regionLabel="Page">
          <a className="skip-link" href="#main">
            Skip to main content
          </a>
          <AppRouter />
        </ErrorBoundary>
      </AppProviders>
    </BrowserRouter>
  );
}
