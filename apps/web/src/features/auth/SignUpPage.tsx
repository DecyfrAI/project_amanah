import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { AppLoadingScreen } from '@/components/ui/AppLoadingScreen';
import { Button } from '@/components/ui/Button';
import { usePageTitle } from '@/hooks/usePageTitle';
import { clearTourCompletion } from '@/features/tour/tour-storage';

import { AuthCard } from './AuthCard';
import { AuthField } from './AuthField';
import { useSession } from './SessionProvider';
import { isEmailShaped, isPasswordLongEnough, MINIMUM_PASSWORD_LENGTH } from './validation';

import styles from './AuthForm.module.css';

/**
 * Sign-up.
 *
 * In live and demo modes this registers a Supabase account (ADR 0005 as amended
 * by spec v2.2 self-serve sign-up) and either opens the workspace immediately
 * or asks the person to confirm their email, depending on the project's Auth
 * settings. In fixture mode it starts the tab-scoped demo session under the
 * name given and transmits nothing.
 */
export function SignUpPage() {
  const navigate = useNavigate();
  const { signUp } = useSession();
  usePageTitle('Sign up');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nameError, setNameError] = useState<string>();
  const [emailError, setEmailError] = useState<string>();
  const [passwordError, setPasswordError] = useState<string>();
  const [submitError, setSubmitError] = useState<string>();
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [isPending, setIsPending] = useState(false);

  const handleNameChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setName(event.currentTarget.value);
    setNameError(undefined);
  }, []);

  const handleEmailChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setEmail(event.currentTarget.value);
    setEmailError(undefined);
  }, []);

  const handlePasswordChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setPassword(event.currentTarget.value);
    setPasswordError(undefined);
  }, []);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();

      const nextNameError =
        name.trim() === '' ? 'Enter the name you want shown in the workspace.' : undefined;
      const nextEmailError = isEmailShaped(email)
        ? undefined
        : 'Enter an email address, including the part after the @ sign.';
      const nextPasswordError = isPasswordLongEnough(password)
        ? undefined
        : `Use at least ${MINIMUM_PASSWORD_LENGTH} characters.`;

      setNameError(nextNameError);
      setEmailError(nextEmailError);
      setPasswordError(nextPasswordError);
      setSubmitError(undefined);

      if (
        nextNameError !== undefined ||
        nextEmailError !== undefined ||
        nextPasswordError !== undefined
      ) {
        return;
      }

      setIsPending(true);
      clearTourCompletion();
      signUp(name.trim(), email, password)
        .then((result) => {
          if (result === 'signed_in') {
            void navigate('/app');
            return;
          }
          setIsPending(false);
          setAwaitingConfirmation(true);
        })
        .catch((error: unknown) => {
          setIsPending(false);
          setSubmitError(
            error instanceof Error ? error.message : 'Sign-up failed. Try again in a moment.',
          );
        });
    },
    [name, email, navigate, password, signUp],
  );

  if (isPending) {
    return <AppLoadingScreen message="Creating your account" hold />;
  }

  return (
    <AuthCard
      heading="Sign up"
      intro={
        <>
          <span>Create an account to try the workspace. Sign-up is open for this MVP.</span>
          <span>In production, a sign-up will need approval before you can use the workspace.</span>
        </>
      }
      footer={
        <>
          Already have an account? <Link to="/login">Log in</Link>
        </>
      }
    >
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <AuthField
          id="name"
          label="Display name"
          type="text"
          value={name}
          onChange={handleNameChange}
          autoComplete="name"
          hint="Shown in the workspace and beside any discussion note you leave."
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
        <AuthField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={handlePasswordChange}
          autoComplete="new-password"
          hint={`At least ${MINIMUM_PASSWORD_LENGTH} characters.`}
          error={passwordError}
        />
        {submitError !== undefined && (
          <p role="alert" className={styles.formError}>
            {submitError}
          </p>
        )}
        {awaitingConfirmation && (
          <output className={styles.formNotice}>
            Check your inbox: confirm your email address, then log in to open the workspace.
          </output>
        )}
        <Button variant="primary" type="submit" disabled={isPending}>
          {isPending ? 'Signing up' : 'Sign up'}
        </Button>
      </form>
    </AuthCard>
  );
}
