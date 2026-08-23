import { useMemo } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { readDataMode } from '@/api';
import { hasFixtureSession } from '@/features/auth/session';

/**
 * Protects /app routes.
 *
 * Fixture mode accepts the invited demo session started from /login. Live
 * mode still waits on Supabase credentials (FE-03). Until those exist, live
 * visitors are sent back to login rather than into an empty shell.
 */
export function AuthGuard() {
  const location = useLocation();
  const mode = readDataMode();
  const allowed = mode === 'fixture' || mode === 'fallback' ? hasFixtureSession() : false;
  const redirectState = useMemo(() => ({ from: location.pathname }), [location.pathname]);

  if (!allowed) {
    return <Navigate to="/login" replace state={redirectState} />;
  }

  return <Outlet />;
}
