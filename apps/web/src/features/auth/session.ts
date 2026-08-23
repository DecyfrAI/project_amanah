const SESSION_KEY = 'amanah.fixture-session';

/**
 * The demo session.
 *
 * Tab-scoped in `sessionStorage` and gone when the tab closes. It holds only
 * what the workspace has to show back to the person using it: a display name,
 * the address they signed in with, and a picture if they chose one. No
 * credential is ever stored, and nothing here is transmitted. See
 * docs/adr/0005-self-serve-sign-up.md.
 *
 * The avatar is a data URL rather than a file reference because there is no
 * storage backend yet. Supabase will own all of this, at which point this module
 * becomes a thin read of the real session.
 */
export interface FixtureSession {
  readonly displayName: string;
  readonly email: string | null;
  readonly avatarDataUrl: string | null;
}

const DEFAULT_DISPLAY_NAME = 'Demo reviewer';

interface StoredSession {
  displayName?: unknown;
  email?: unknown;
  avatarDataUrl?: unknown;
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() !== '' ? value : null;
}

export function hasFixtureSession(): boolean {
  return sessionStorage.getItem(SESSION_KEY) !== null;
}

export function readFixtureSession(): FixtureSession | null {
  const stored = sessionStorage.getItem(SESSION_KEY);
  if (stored === null) {
    return null;
  }

  // Earlier builds stored the flag '1', then a bare display name. Both are
  // still valid sessions, and neither should log someone out mid-visit.
  if (stored === '1') {
    return { displayName: DEFAULT_DISPLAY_NAME, email: null, avatarDataUrl: null };
  }

  try {
    const parsed = JSON.parse(stored) as StoredSession;
    return {
      displayName: readString(parsed.displayName) ?? DEFAULT_DISPLAY_NAME,
      email: readString(parsed.email),
      avatarDataUrl: readString(parsed.avatarDataUrl),
    };
  } catch {
    return {
      displayName: readString(stored) ?? DEFAULT_DISPLAY_NAME,
      email: null,
      avatarDataUrl: null,
    };
  }
}

export function startFixtureSession(displayName?: string, email?: string): void {
  const trimmed = displayName?.trim();
  writeSession({
    displayName: trimmed === undefined || trimmed === '' ? DEFAULT_DISPLAY_NAME : trimmed,
    email: email?.trim() ?? null,
    avatarDataUrl: null,
  });
}

/** Applies a partial change without disturbing the rest of the session. */
export function updateFixtureSession(changes: Partial<FixtureSession>): FixtureSession {
  const current = readFixtureSession() ?? {
    displayName: DEFAULT_DISPLAY_NAME,
    email: null,
    avatarDataUrl: null,
  };

  const next: FixtureSession = {
    displayName: changes.displayName?.trim() ?? current.displayName,
    email: changes.email === undefined ? current.email : changes.email,
    avatarDataUrl:
      changes.avatarDataUrl === undefined ? current.avatarDataUrl : changes.avatarDataUrl,
  };

  writeSession(next);
  return next;
}

function writeSession(session: FixtureSession): void {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function endFixtureSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}
