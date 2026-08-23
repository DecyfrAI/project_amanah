import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { AppLoadingScreen, entryHoldMs } from '@/components/ui/AppLoadingScreen';
import { Button } from '@/components/ui/Button';
import { usePageTitle } from '@/hooks/usePageTitle';

import { AuthCard } from './AuthCard';
import { AuthField } from './AuthField';
import { isEmailShaped } from './validation';
import { startFixtureSession } from './session';

import styles from './AuthForm.module.css';

/**
 * Login.
 *
 * The credentials are checked for shape and then discarded: in fixture mode
 * there is no account to authenticate against, so the form starts a local demo
 * session instead. See docs/adr/0005-self-serve-sign-up.md.
 */
export function LoginPage() {
  const navigate = useNavigate();
  usePageTitle('Log in');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState<string>();
  const [passwordError, setPasswordError] = useState<string>();
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

      if (nextEmailError !== undefined || nextPasswordError !== undefined) {
        return;
      }

      setIsPending(true);
      startFixtureSession(undefined, email);
    },
    [email, password],
  );

  useEffect(() => {
    if (!isPending) {
      return;
    }
    const timer = window.setTimeout(() => {
      void navigate('/app');
    }, entryHoldMs());
    return () => {
      window.clearTimeout(timer);
    };
  }, [isPending, navigate]);

  if (isPending) {
    return <AppLoadingScreen message="Insights await" hold />;
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
        <Button variant="primary" type="submit" disabled={isPending}>
          {isPending ? 'Opening the workspace' : 'Log in'}
        </Button>
      </form>
    </AuthCard>
  );
}
