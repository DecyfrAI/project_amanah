import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';

import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { AuthField } from '@/features/auth/AuthField';
import { isEmailShaped } from '@/features/auth/validation';
import { readFixtureSession, updateFixtureSession } from '@/features/auth/session';
import { usePageTitle } from '@/hooks/usePageTitle';

import { readImageFile, AVATAR_MAX_BYTES } from './avatar-file';
import { ViewerNotes } from './ViewerNotes';

import styles from './ProfilePage.module.css';

/**
 * Profile and account.
 *
 * Display name, email and picture are held in the tab-scoped demo session, so
 * changes here are real on screen and disappear when the tab closes. The
 * password section is deliberately inert: there is no credential to change until
 * Supabase Auth is connected, and a form that appeared to change one would be a
 * lie. See docs/adr/0005-self-serve-sign-up.md.
 */
export function ProfilePage() {
  usePageTitle('Profile');

  const session = readFixtureSession();
  const [displayName, setDisplayName] = useState(session?.displayName ?? '');
  const [email, setEmail] = useState(session?.email ?? '');
  const [avatarDataUrl, setAvatarDataUrl] = useState<string | null>(session?.avatarDataUrl ?? null);
  const [nameError, setNameError] = useState<string>();
  const [emailError, setEmailError] = useState<string>();
  const [avatarError, setAvatarError] = useState<string>();
  const [savedMessage, setSavedMessage] = useState<string>();

  const handleNameChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setDisplayName(event.currentTarget.value);
    setNameError(undefined);
    setSavedMessage(undefined);
  }, []);

  const handleEmailChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setEmail(event.currentTarget.value);
    setEmailError(undefined);
    setSavedMessage(undefined);
  }, []);

  const handleAvatarChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    const file = event.currentTarget.files?.[0];
    setAvatarError(undefined);
    setSavedMessage(undefined);

    if (file === undefined) {
      return;
    }

    void readImageFile(file).then(
      (dataUrl) => {
        setAvatarDataUrl(dataUrl);
        updateFixtureSession({ avatarDataUrl: dataUrl });
        setSavedMessage('Picture updated.');
      },
      (error: unknown) => {
        setAvatarError(
          error instanceof Error ? error.message : 'That picture could not be read. Try another.',
        );
      },
    );
  }, []);

  const handleRemoveAvatar = useCallback((): void => {
    setAvatarDataUrl(null);
    updateFixtureSession({ avatarDataUrl: null });
    setSavedMessage('Picture removed. Your initials are shown instead.');
  }, []);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();

      const nextNameError = displayName.trim() === '' ? 'Enter a display name.' : undefined;
      const nextEmailError =
        email.trim() === '' || isEmailShaped(email)
          ? undefined
          : 'Enter an email address, including the part after the @ sign.';

      setNameError(nextNameError);
      setEmailError(nextEmailError);

      if (nextNameError !== undefined || nextEmailError !== undefined) {
        return;
      }

      updateFixtureSession({ displayName, email: email.trim() === '' ? null : email.trim() });
      setSavedMessage('Profile updated for this session.');
    },
    [displayName, email],
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Profile and account</h1>
        <p className={styles.lead}>
          How you appear in the workspace. These details are held in this browser tab only and are
          not sent anywhere, so they reset when the tab closes. Supabase Auth will own them once it
          is connected.
        </p>
      </header>

      <div className={styles.layout}>
        <div className={styles.account}>
          <section className={styles.card} aria-labelledby="picture-heading">
            <h2 id="picture-heading" className={styles.sectionHeading}>
              Picture
            </h2>

            <div className={styles.pictureRow}>
              <Avatar displayName={displayName} imageSrc={avatarDataUrl} size="large" />

              <div className={styles.pictureActions}>
                <div className={styles.dropzone}>
                  <label className={styles.fileLabel} htmlFor="avatar">
                    Choose a picture
                  </label>
                  <p className={styles.hint} id="avatar-hint">
                    PNG, JPEG or WebP, up to {Math.round(AVATAR_MAX_BYTES / 1024)} KB. Stored in
                    this tab only. Without one, your initials are shown.
                  </p>
                  <input
                    className={styles.fileInput}
                    id="avatar"
                    name="avatar"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handleAvatarChange}
                    aria-describedby="avatar-hint"
                  />
                </div>
                {avatarDataUrl !== null && (
                  <Button variant="secondary" onClick={handleRemoveAvatar}>
                    Remove picture
                  </Button>
                )}
                {avatarError !== undefined && (
                  <p className={styles.error} role="alert">
                    {avatarError}
                  </p>
                )}
              </div>
            </div>
          </section>

          <section className={styles.card} aria-labelledby="details-heading">
            <h2 id="details-heading" className={styles.sectionHeading}>
              Details
            </h2>

            <form className={styles.form} onSubmit={handleSubmit} noValidate>
              <AuthField
                id="displayName"
                label="Display name"
                type="text"
                value={displayName}
                onChange={handleNameChange}
                autoComplete="name"
                hint="Shown in the sidebar and beside any discussion note you leave."
                error={nameError}
              />
              <AuthField
                id="email"
                label="Email address"
                type="email"
                value={email}
                onChange={handleEmailChange}
                autoComplete="email"
                error={emailError}
              />
              <Button variant="primary" type="submit">
                Save details
              </Button>
            </form>

            <output className={styles.saved} aria-live="polite">
              {savedMessage ?? ''}
            </output>
          </section>

          <section className={styles.card} aria-labelledby="password-heading">
            <h2 id="password-heading" className={styles.sectionHeading}>
              Password
            </h2>
            <p className={styles.pending}>
              There is no password to change yet. This session is local to the tab and holds no
              credential, so a change form here would do nothing. It arrives with Supabase Auth,
              which will also handle reset by email.
            </p>
          </section>
        </div>

        <ViewerNotes />
      </div>
    </div>
  );
}
