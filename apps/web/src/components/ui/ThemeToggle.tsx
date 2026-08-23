import { useTheme } from '@/app/ThemeProvider';

import styles from './ThemeToggle.module.css';

interface ThemeToggleProps {
  /** Rail mode: icon only, with the label kept for assistive technology. */
  isCompact?: boolean;
}

/**
 * Switches the workspace between the light and dark token sets.
 *
 * The accessible name states the action rather than the current state, since
 * "Dark" alone leaves a screen-reader user guessing whether it describes what
 * they have or what they would get.
 */
export function ThemeToggle({ isCompact = false }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const label = isDark ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <button
      type="button"
      className={isCompact ? `${styles.toggle} ${styles.toggleCompact}` : styles.toggle}
      onClick={toggleTheme}
      title={isCompact ? label : undefined}
    >
      <span className={styles.icon} aria-hidden="true">
        {isDark ? <SunIcon /> : <MoonIcon />}
      </span>
      <span className={isCompact ? 'visually-hidden' : undefined}>{label}</span>
    </button>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m10 10 1.4 1.4m0-12.8-1.4 1.4m-10 10-1.4 1.4" />
    </svg>
  );
}
