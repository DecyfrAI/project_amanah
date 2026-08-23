import type { ReactNode } from 'react';

import styles from './StatusPill.module.css';

/**
 * What a status means, separately from the words a caller chooses for it.
 *
 * Each value carries one colour and one glyph, so two things in the same state
 * always look alike and no state is told by colour alone. Neither `blocked` nor
 * `absent` is red: brand system 4 reserves red for reviewed severe harm, and a
 * connector waiting on an access grant is not harm.
 */
export type StatusIndicator = 'ok' | 'pending' | 'degraded' | 'blocked' | 'absent';

interface StatusPillProps {
  indicator: StatusIndicator;
  /** The words a reader sees. Always visible; the colour only repeats them. */
  label: string;
  /** Optional longer phrase for hover, when the visible label is compact. */
  title?: string;
}

const ICONS: Record<StatusIndicator, ReactNode> = {
  ok: <CheckIcon />,
  pending: <ClockIcon />,
  degraded: <WarningIcon />,
  blocked: <LockIcon />,
  absent: <DashIcon />,
};

export function StatusPill({ indicator, label, title }: StatusPillProps) {
  return (
    <span className={`${styles.pill} ${styles[indicator]}`} title={title}>
      <span className={styles.icon} aria-hidden="true">
        {ICONS[indicator]}
      </span>
      {label}
    </span>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M5 13l4.5 4.5L19 7" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M12 4.5 21 19.5H3Z" />
      <path d="M12 10v4M12 16.5v.5" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <rect x="5" y="10.5" width="14" height="9" rx="2" />
      <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
    </svg>
  );
}

function DashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8 12h8" />
    </svg>
  );
}
