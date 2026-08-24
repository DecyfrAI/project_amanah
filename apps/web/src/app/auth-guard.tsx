import { useMemo } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { AppLoadingScreen } from '@/components/ui/AppLoadingScreen';
import { useSession } from '@/features/auth/SessionProvider';

/**
 * Protects /app routes.
 *
 * In live and demo modes the session is a restored Supabase session; in fixture
 * mode it is the tab-scoped demo session. While restoration is in flight the
 * guard shows the loading screen for exactly as long as the restore actually
 * takes (PA-03) — never a fixed timer. This guard is UX only: the security
 * boundary is the server-side bearer-token check on every `/v1` route.
 */
export function AuthGuard() {
  const location = useLocation();
  const { status } = useSession();
  const redirectState = useMemo(() => ({ from: location.pathname }), [location.pathname]);

  if (status === 'restoring') {
    return <AppLoadingScreen message="Restoring your session" />;
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={redirectState} />;
  }

  return <Outlet />;
}
