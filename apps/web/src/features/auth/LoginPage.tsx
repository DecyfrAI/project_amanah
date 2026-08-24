import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { AppLoadingScreen } from '@/components/ui/AppLoadingScreen';
import { Button } from '@/components/ui/Button';
import { usePageTitle } from '@/hooks/usePageTitle';

import { AuthCard } from './AuthCard';
import { AuthField } from './AuthField';
import { useSession } from './SessionProvider';
import { isEmailShaped } from './validation';

import styles from './AuthForm.module.css';

/** Only an in-app path may be returned to after login; anything else is /app. */
export function safeInternalReturn(candidate: unknown): string {
  if (typeof candidate !== 'string' || !candidate.startsWith('/app')) {
    return '/app';
  }
  return candidate;
}

/**
 * Login.
 *
 * In live and demo modes this authenticates against Supabase and navigates the
 * moment the session exists (PA-03) — the loading screen lasts exactly as long
 * as the sign-in request, never a fixed timer. In fixture mode the form starts
 * the tab-scoped demo session (ADR 0005).
 */
export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useSession();
  usePageTitle('Log in');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState<string>();
  const [passwordError, setPasswordError] = useState<string>();
  const [submitError, setSubmitError] = useState<string>();
  const [isPending, setIsPending] = useState(false);

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

      const nextEmailError = isEmailShaped(email)
        ? undefined
        : 'Enter an email address, including the part after the @ sign.';
      const nextPasswordError = password === '' ? 'Enter your password.' : undefined;

      setEmailError(nextEmailError);
      setPasswordError(nextPasswordError);
      setSubmitError(undefined);

      if (nextEmailError !== undefined || nextPasswordError !== undefined) {
        return;
      }

      setIsPending(true);
      const returnTo = safeInternalReturn(
        (location.state as { from?: unknown } | null)?.from ?? null,
      );
      signIn(email, password)
        .then(() => {
          void navigate(returnTo);
        })
        .catch((error: unknown) => {
          setIsPending(false);
          setSubmitError(
            error instanceof Error ? error.message : 'Sign-in failed. Try again in a moment.',
          );
        });
    },
    [email, location.state, navigate, password, signIn],
  );

  if (isPending) {
    return <AppLoadingScreen message="Signing you in" hold />;
  }

  return (
    <AuthCard
      heading="Log in to the workspace"
      intro={
        <>
          <span>Sign-up is open for this MVP, so you can log in and try the workspace.</span>
          <span>In production, a sign-up will need approval before you can use the workspace.</span>
        </>
      }
      footer={
        <>
          No account yet? <Link to="/signup">Sign up</Link>
        </>
      }
    >
      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <AuthField
          id="email"
          label="Email address"
          type="email"
          value={email}
          onChange={handleEmailChange}
          autoComplete="username"
          error={emailError}
        />
        <AuthField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={handlePasswordChange}
          autoComplete="current-password"
          error={passwordError}
        />
        {submitError !== undefined && (
          <p role="alert" className={styles.formError}>
            {submitError}
          </p>
        )}
        <Button variant="primary" type="submit" disabled={isPending}>
          {isPending ? 'Signing in' : 'Log in'}
        </Button>
      </form>
    </AuthCard>
  );
}
