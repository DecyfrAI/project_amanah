import type { ChangeEvent } from 'react';

import styles from './AuthField.module.css';

interface AuthFieldProps {
  id: string;
  label: string;
  type: 'text' | 'email' | 'password';
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  /** Browser autofill hint. `new-password` on sign-up, `current-password` on login. */
  autoComplete: string;
  /** Validation message. Rendered under the field and referenced by the input. */
  error?: string | undefined;
  /** Standing guidance, shown whether or not the field is in error. */
  hint?: string | undefined;
}

/**
 * Labelled text input with its own error and hint text.
 *
 * The label is a real `<label>` rather than a placeholder: placeholder text
 * disappears the moment someone starts typing, which is exactly when they need
 * it. `aria-describedby` points at whichever of hint and error exist, so the
 * message is announced with the field instead of being left to sighted reading.
 */
export function AuthField({
  id,
  label,
  type,
  value,
  onChange,
  autoComplete,
  error,
  hint,
}: AuthFieldProps) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [hint === undefined ? null : hintId, error === undefined ? null : errorId]
    .filter((token): token is string => token !== null)
    .join(' ');

  return (
    <p className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <input
        className={error === undefined ? styles.input : `${styles.input} ${styles.inputInvalid}`}
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        aria-invalid={error !== undefined}
        aria-describedby={describedBy === '' ? undefined : describedBy}
      />
      {hint !== undefined && (
        <span className={styles.hint} id={hintId}>
          {hint}
        </span>
      )}
      {error !== undefined && (
        <span className={styles.error} id={errorId}>
          {error}
        </span>
      )}
    </p>
  );
}
