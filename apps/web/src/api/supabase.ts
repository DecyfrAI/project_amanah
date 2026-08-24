import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * The Supabase browser client, created once from public `VITE_` values.
 *
 * The anon key is public by design and constrained by row-level security; no
 * service-role key, database URL, or provider secret is ever read here. A
 * placeholder or missing value yields `null` rather than a client that would
 * fail on first use — a copied `.env` with empty values must read as
 * "not configured", not as a broken deployment.
 */
export interface SupabaseConfig {
  readonly url: string;
  readonly anonKey: string;
}

function readConfiguredValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (trimmed === '' || trimmed.includes('YOUR-') || trimmed.includes('example.supabase')) {
    return null;
  }
  return trimmed;
}

export function readSupabaseConfig(): SupabaseConfig | null {
  const url = readConfiguredValue(import.meta.env.VITE_SUPABASE_URL);
  const anonKey = readConfiguredValue(import.meta.env.VITE_SUPABASE_ANON_KEY);
  if (url === null || anonKey === null || !url.startsWith('https://')) {
    return null;
  }
  return { url, anonKey };
}

let cachedClient: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient | null {
  if (cachedClient !== null) {
    return cachedClient;
  }
  const config = readSupabaseConfig();
  if (config === null) {
    return null;
  }
  cachedClient = createClient(config.url, config.anonKey);
  return cachedClient;
}

export function isSupabaseConfigured(): boolean {
  return readSupabaseConfig() !== null;
}

/**
 * The current access token, or `null` when no session is held.
 *
 * Read from the Supabase client's own persistence on every call; the token is
 * never copied into other storage, and refresh is the client library's job.
 */
export async function readAccessToken(): Promise<string | null> {
  const client = getSupabaseClient();
  if (client === null) {
    return null;
  }
  const { data } = await client.auth.getSession();
  return data.session?.access_token ?? null;
}

/**
 * Ends the local session after the API rejected its token.
 *
 * The server is the authority on whether a token is still valid, so a `401`
 * means the stored session is no longer usable no matter what the client
 * believes. Clearing it makes `SessionProvider` report `anonymous`, which sends
 * the route guard to the login screen instead of leaving a signed-in-looking
 * shell that fails every request.
 *
 * Deliberately not called for `403`: that is a live session being told it lacks
 * permission, and signing the person out would be the wrong response.
 */
export async function endExpiredSession(): Promise<void> {
  const client = getSupabaseClient();
  if (client === null) {
    return;
  }
  await client.auth.signOut();
}
