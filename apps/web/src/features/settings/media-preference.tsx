import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react';

import { apiClient, queryKeys, type WireProfile } from '@/api';

/**
 * The global image-display preference (PA-01).
 *
 * Images are visible by default. A person may opt in to blurring media, and
 * that choice is stored on their authenticated profile through
 * `PATCH /v1/me` — not in page-local state — so it survives a refresh and a
 * new session, and applies on every approved image surface at once.
 *
 * This preference governs *display* only. It changes no authorization, no text
 * redaction, and no signed-URL handling: a blurred image and a visible one are
 * fetched through exactly the same authenticated path.
 */

/** Profile preference key. Stored server-side inside `content_safety_preferences`. */
export const BLUR_MEDIA_KEY = 'blur_media';

export interface MediaPreferenceValue {
  /** True when the viewer has opted in to blurring media. Default false. */
  readonly blurMedia: boolean;
  /** False while the stored preference is still being read. */
  readonly isLoaded: boolean;
  setBlurMedia: (blurMedia: boolean) => void;
  /** True while a change is being written to the profile. */
  readonly isSaving: boolean;
  /** A safe message when the last write failed, or null. */
  readonly saveError: string | null;
}

const MediaPreferenceContext = createContext<MediaPreferenceValue | null>(null);

/**
 * Read the stored flag.
 *
 * Anything that is not exactly `true` reads as "do not blur". A malformed or
 * absent value must land on the documented default rather than on whichever
 * state a coercion happens to produce.
 */
function readBlurMedia(profile: WireProfile | undefined): boolean {
  return profile?.content_safety_preferences[BLUR_MEDIA_KEY] === true;
}

export function MediaPreferenceProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const profileQuery = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: () => apiClient.getCurrentUser(),
    staleTime: 5 * 60_000,
  });

  const mutation = useMutation({
    mutationFn: (blurMedia: boolean) =>
      apiClient.updateProfile({ contentSafetyPreferences: { [BLUR_MEDIA_KEY]: blurMedia } }),
    onSuccess: (profile: WireProfile): void => {
      // Seed the cache from the server's own answer so every surface changes
      // at once, with no reload and no second read.
      queryClient.setQueryData(queryKeys.currentUser, profile);
    },
  });

  const { mutate } = mutation;
  const setBlurMedia = useCallback(
    (blurMedia: boolean): void => {
      mutate(blurMedia);
    },
    [mutate],
  );

  // An in-flight change is shown immediately; a failed write falls back to the
  // stored value rather than leaving the screen showing a preference the
  // profile does not hold.
  const pending = mutation.isPending ? mutation.variables : undefined;
  const blurMedia = pending ?? readBlurMedia(profileQuery.data);

  const value = useMemo<MediaPreferenceValue>(
    () => ({
      blurMedia,
      isLoaded: !profileQuery.isPending,
      setBlurMedia,
      isSaving: mutation.isPending,
      saveError: mutation.isError ? 'That preference could not be saved. Try again.' : null,
    }),
    [blurMedia, mutation.isError, mutation.isPending, profileQuery.isPending, setBlurMedia],
  );

  return (
    <MediaPreferenceContext.Provider value={value}>{children}</MediaPreferenceContext.Provider>
  );
}

/**
 * The viewer's media preference.
 *
 * Usable outside the provider: surfaces that render before the workspace shell
 * mounts fall back to the documented default (visible) rather than throwing.
 */
export function useMediaPreference(): MediaPreferenceValue {
  return (
    useContext(MediaPreferenceContext) ?? {
      blurMedia: false,
      isLoaded: true,
      setBlurMedia: () => undefined,
      isSaving: false,
      saveError: null,
    }
  );
}
