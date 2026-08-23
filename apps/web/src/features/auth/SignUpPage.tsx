import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { AppLoadingScreen, entryHoldMs } from '@/components/ui/AppLoadingScreen';
import { Button } from '@/components/ui/Button';
import { usePageTitle } from '@/hooks/usePageTitle';

import { AuthCard } from './AuthCard';
import { AuthField } from './AuthField';
import { isEmailShaped, isPasswordLongEnough, MINIMUM_PASSWORD_LENGTH } from './validation';
import { clearTourCompletion } from '@/features/tour/tour-storage';

import { startFixtureSession } from './session';

import styles from './AuthForm.module.css';

/**
 * Sign-up.
 *
 * A deliberate deviation from the planning documents, which close registration
 * for this build. It is safe here only because nothing is registered: the form
 * validates, starts a local demo session under the name given, and transmits and
 * stores nothing else. The reasoning, the risk, and how to revert are in
 * docs/adr/0005-self-serve-sign-up.md.
 */
export function SignUpPage() {
  const navigate = useNavigate();
  usePageTitle('Sign up');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nameError, setNameError] = useState<string>();
  const [emailError, setEmailError] = useState<string>();
  const [passwordError, setPasswordError] = useState<string>();
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

      if (
        nextNameError !== undefined ||
        nextEmailError !== undefined ||
        nextPasswordError !== undefined
      ) {
        return;
      }

      setIsPending(true);
      clearTourCompletion();
      startFixtureSession(name, email);
    },
    [name, email, password],
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
        <Button variant="primary" type="submit" disabled={isPending}>
          {isPending ? 'Signing up' : 'Sign up'}
        </Button>
      </form>
    </AuthCard>
  );
}
