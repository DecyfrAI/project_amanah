import { NavLink } from 'react-router-dom';

import { WORKSPACE_NAV } from './navItems';

import styles from './WorkspaceNav.module.css';

interface WorkspaceNavProps {
  /** Called when a destination is chosen, so a mobile drawer can close itself. */
  onNavigate?: (() => void) | undefined;
  /** Rail mode: icons only, with the label kept for assistive technology. */
  isCollapsed?: boolean;
}

function linkClass({ isActive }: { isActive: boolean }): string {
  const base = styles.link ?? '';
  const current = styles.linkCurrent ?? '';
  return isActive ? `${base} ${current}` : base;
}

/**
 * The workspace tab list.
 *
 * `NavLink` supplies `aria-current="page"` on the active item, so the current
 * tab is announced rather than only tinted. The same component serves the
 * desktop sidebar, the collapsed rail, and the mobile drawer: one list, one
 * source of truth.
 */
export function WorkspaceNav({ onNavigate, isCollapsed = false }: WorkspaceNavProps) {
  return (
    <ul className={isCollapsed ? `${styles.list} ${styles.listNarrow}` : styles.list}>
      {WORKSPACE_NAV.map((item) => (
        <li key={item.to}>
          <NavLink
            to={item.to}
            end={item.isIndex === true}
            className={linkClass}
            onClick={onNavigate}
            title={isCollapsed ? item.label : undefined}
          >
            <span className={styles.icon} aria-hidden="true">
              {item.icon}
            </span>
            <span className={isCollapsed ? 'visually-hidden' : undefined}>{item.label}</span>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}
