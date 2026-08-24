import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { readDataMode, usesLiveAuthentication } from '@/api';
import { getSupabaseClient } from '@/api/supabase';

import {
  endFixtureSession,
  readFixtureSession,
  startFixtureSession,
  updateFixtureSession,
} from './session';

/**
 * One session surface for the whole application (F-S9).
 *
 * In `live` and `demo` modes this wraps the Supabase browser client: the
 * session is restored from the client's own persistence before any protected
 * route renders, tokens stay inside the client, and sign-in/out go through
 * Supabase Auth. In `fixture` and `fallback` modes the tab-scoped fixture
 * session remains, so the rehearsal flows keep working with no credentials.
 */

export type SessionStatus = 'restoring' | 'authenticated' | 'anonymous';

export interface AppSession {
  readonly displayName: string;
  readonly email: string | null;
  readonly avatarDataUrl: string | null;
}

export type SignUpResult = 'signed_in' | 'confirm_email';

export interface SessionContextValue {
  readonly status: SessionStatus;
  readonly session: AppSession | null;
  /** Whether this build authenticates against Supabase rather than the fixture. */
  readonly isLiveAuth: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (displayName: string, email: string, password: string) => Promise<SignUpResult>;
  signOut: () => Promise<void>;
  /** Updates the display name shown in the shell without a full refresh. */
  applyDisplayName: (displayName: string) => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

const NOT_CONFIGURED_MESSAGE =
  'Authentication is not configured for this build. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.';

function displayNameFromMetadata(metadata: Record<string, unknown>, email: string | null): string {
  const stored = metadata['display_name'];
  if (typeof stored === 'string' && stored.trim() !== '') {
    return stored.trim();
  }
  if (email !== null && email.includes('@')) {
    return email.slice(0, email.indexOf('@'));
  }
  return 'Member';
}

function useLiveSession(): SessionContextValue {
  const client = getSupabaseClient();
  const [status, setStatus] = useState<SessionStatus>(client === null ? 'anonymous' : 'restoring');
  const [session, setSession] = useState<AppSession | null>(null);
  const [displayNameOverride, setDisplayNameOverride] = useState<string | null>(null);

  useEffect(() => {
    if (client === null) {
      return;
    }
    let cancelled = false;

    void client.auth.getSession().then(({ data }) => {
      if (cancelled) {
        return;
      }
      const user = data.session?.user;
      if (user === undefined) {
        setSession(null);
        setStatus('anonymous');
        return;
      }
      setSession({
        displayName: displayNameFromMetadata(user.user_metadata, user.email ?? null),
        email: user.email ?? null,
        avatarDataUrl: null,
      });
      setStatus('authenticated');
    });

    const { data: subscription } = client.auth.onAuthStateChange((_event, supabaseSession) => {
      if (cancelled) {
        return;
      }
      const user = supabaseSession?.user;
      if (user === undefined) {
        setSession(null);
        setStatus('anonymous');
        return;
      }
      setSession({
        displayName: displayNameFromMetadata(user.user_metadata, user.email ?? null),
        email: user.email ?? null,
        avatarDataUrl: null,
      });
      setStatus('authenticated');
    });

    return () => {
      cancelled = true;
      subscription.subscription.unsubscribe();
    };
  }, [client]);

  const signIn = useCallback(
    async (email: string, password: string): Promise<void> => {
      if (client === null) {
        throw new Error(NOT_CONFIGURED_MESSAGE);
      }
      const { error } = await client.auth.signInWithPassword({ email, password });
      if (error !== null) {
        // Supabase wording is safe here: invalid credentials, unconfirmed
        // email, and rate limiting are user-actionable messages.
        throw new Error(error.message);
      }
    },
    [client],
  );

  const signUp = useCallback(
    async (displayName: string, email: string, password: string): Promise<SignUpResult> => {
      if (client === null) {
        throw new Error(NOT_CONFIGURED_MESSAGE);
      }
      const { data, error } = await client.auth.signUp({
        email,
        password,
        options: { data: { display_name: displayName } },
      });
      if (error !== null) {
        throw new Error(error.message);
      }
      return data.session === null ? 'confirm_email' : 'signed_in';
    },
    [client],
  );

  const signOut = useCallback(async (): Promise<void> => {
    if (client === null) {
      return;
    }
    await client.auth.signOut();
  }, [client]);

  const applyDisplayName = useCallback((displayName: string): void => {
    setDisplayNameOverride(displayName);
  }, []);

  return useMemo(
    () => ({
      status,
      session:
        session === null || displayNameOverride === null
          ? session
          : { ...session, displayName: displayNameOverride },
      isLiveAuth: true,
      signIn,
      signUp,
      signOut,
      applyDisplayName,
    }),
    [applyDisplayName, displayNameOverride, session, signIn, signOut, signUp, status],
  );
}

function useFixtureSession(): SessionContextValue {
  const [session, setSession] = useState<AppSession | null>(() => readFixtureSession());

  const signIn = useCallback(async (email: string): Promise<void> => {
    startFixtureSession(undefined, email);
    setSession(readFixtureSession());
    return Promise.resolve();
  }, []);

  const signUp = useCallback(async (displayName: string, email: string): Promise<SignUpResult> => {
    startFixtureSession(displayName, email);
    setSession(readFixtureSession());
    return Promise.resolve('signed_in' as const);
  }, []);

  const signOut = useCallback(async (): Promise<void> => {
    endFixtureSession();
    setSession(null);
    return Promise.resolve();
  }, []);

  const applyDisplayName = useCallback((displayName: string): void => {
    setSession(updateFixtureSession({ displayName }));
  }, []);

  return useMemo(
    () => ({
      status: session === null ? ('anonymous' as const) : ('authenticated' as const),
      session,
      isLiveAuth: false,
      signIn,
      signUp,
      signOut,
      applyDisplayName,
    }),
    [applyDisplayName, session, signIn, signOut, signUp],
  );
}

function LiveSessionProvider({ children }: { children: ReactNode }) {
  const value = useLiveSession();
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
LiveSessionProvider.displayName = 'LiveSessionProvider';

function FixtureSessionProvider({ children }: { children: ReactNode }) {
  const value = useFixtureSession();
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
FixtureSessionProvider.displayName = 'FixtureSessionProvider';

export function SessionProvider({ children }: { children: ReactNode }) {
  if (usesLiveAuthentication(readDataMode())) {
    return <LiveSessionProvider>{children}</LiveSessionProvider>;
  }
  return <FixtureSessionProvider>{children}</FixtureSessionProvider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error('useSession must be used inside a SessionProvider');
  }
  return value;
}
