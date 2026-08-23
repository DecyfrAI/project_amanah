import type { ReactNode } from 'react';

/**
 * The authenticated tabs, in the order the Blueprint's user journey walks them:
 * see what the sample covers, search the records under it, read the written
 * analysis, correct what the model got wrong, then export something defensible.
 *
 * Connections and Settings sit at the end because they are utilities rather
 * than research surfaces.
 */
export interface WorkspaceNavItem {
  readonly to: string;
  readonly label: string;
  /** True only for the index route, which would otherwise match every child. */
  readonly isIndex?: boolean;
  readonly icon: ReactNode;
}

export const WORKSPACE_NAV: readonly WorkspaceNavItem[] = [
  { to: '/app', label: 'Overview', isIndex: true, icon: <GaugeIcon /> },
  { to: '/app/explorer', label: 'Explorer', icon: <SearchIcon /> },
  { to: '/app/insights', label: 'Insights', icon: <InsightIcon /> },
  { to: '/app/lessons', label: 'Lessons', icon: <LessonIcon /> },
  { to: '/app/review', label: 'Review', icon: <ReviewIcon /> },
  { to: '/app/reports', label: 'Reports', icon: <ReportIcon /> },
  { to: '/app/connections', label: 'Connections', icon: <ConnectionIcon /> },
  { to: '/app/settings', label: 'Settings', icon: <SettingsIcon /> },
];

function GaugeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M4 18a8 8 0 1 1 16 0" />
      <path d="M12 18 15.5 9.5" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m15 15 4.5 4.5" />
    </svg>
  );
}

function InsightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M5 4h14v16l-7-3.5L5 20Z" />
      <path d="M9 9h6M9 12.5h4" />
    </svg>
  );
}

function LessonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M5 5.5h6.5A3.5 3.5 0 0 1 15 9v10.5H8.5A3.5 3.5 0 0 0 5 16V5.5Z" />
      <path d="M19 5.5h-6.5A3.5 3.5 0 0 0 9 9v10.5h6.5A3.5 3.5 0 0 1 19 16V5.5Z" />
    </svg>
  );
}

function ReviewIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <circle cx="12" cy="12" r="8" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M6 3h8l4 4v14H6Z" />
      <path d="M14 3v4h4M9.5 12v5M12.5 10v7M15.5 14v3" />
    </svg>
  );
}

function ConnectionIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M9 4v5M15 4v5M7.5 9h9v3a4.5 4.5 0 0 1-9 0Z" />
      <path d="M12 16.5V21" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" />
      <circle cx="9" cy="7" r="2" />
      <circle cx="15" cy="12" r="2" />
      <circle cx="9" cy="17" r="2" />
    </svg>
  );
}
