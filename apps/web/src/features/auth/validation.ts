/**
 * Shape check, not a validity check.
 *
 * There is no reliable client-side test for whether an address exists, and a
 * strict pattern rejects legitimate addresses. This asks only for one @ with
 * something either side and a dot in the domain, which is enough to catch a
 * typo without arguing with the reader about their own address.
 */
export function isEmailShaped(value: string): boolean {
  const trimmed = value.trim();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
}

/** Long enough to be deliberate. The real policy belongs to the auth provider. */
export const MINIMUM_PASSWORD_LENGTH = 8;

export function isPasswordLongEnough(value: string): boolean {
  return value.length >= MINIMUM_PASSWORD_LENGTH;
}
