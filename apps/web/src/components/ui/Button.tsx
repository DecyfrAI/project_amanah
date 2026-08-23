import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import styles from './Button.module.css';

type ButtonVariant = 'primary' | 'secondary';

interface ButtonProps {
  variant: ButtonVariant;
  type?: 'button' | 'submit';
  onClick?: () => void;
  disabled?: boolean;
  children: ReactNode;
}

export function Button({
  variant,
  type = 'button',
  onClick,
  disabled = false,
  children,
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${styles.button} ${styles[variant]}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

interface ButtonLinkProps {
  variant: ButtonVariant;
  /** In-app route. Rendered as a router link, never as a button. */
  to: string;
  children: ReactNode;
}

interface ButtonAnchorProps {
  variant: ButtonVariant;
  /** In-page anchor, such as `#methodology`. */
  href: string;
  children: ReactNode;
}

/**
 * Navigation action styled as a pill.
 *
 * A control that navigates is a link, not a button, so it keeps native
 * behaviour: middle-click, open in new tab, and the correct screen-reader role.
 * rules/frontend.md requires semantic HTML over a styled substitute.
 */
export function ButtonLink({ variant, to, children }: ButtonLinkProps) {
  return (
    <Link className={`${styles.button} ${styles[variant]}`} to={to}>
      {children}
    </Link>
  );
}

/**
 * The same pill, for an anchor within the current page.
 *
 * Separate from ButtonLink because a router link to a same-path hash does not
 * scroll: React Router treats it as a no-op navigation. A plain anchor lets the
 * browser do what it already does correctly.
 */
export function ButtonAnchor({ variant, href, children }: ButtonAnchorProps) {
  return (
    <a className={`${styles.button} ${styles[variant]}`} href={href}>
      {children}
    </a>
  );
}
