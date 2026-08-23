import { useCallback, useState } from 'react';

import styles from './ExpandingPanels.module.css';

export interface ExpandingPanel {
  id: string;
  /** Short label. Rendered rotated when the panel is closed, so it must be
   *  brief enough to fit the panel's height, one or two words. */
  name: string;
  /** Descriptive line, shown only while the panel is open. */
  headline: string;
  body: string;
  /** What the analyst ends up with. Shown as a closing line inside the panel. */
  outcome: string;
}

interface PanelProps {
  panel: ExpandingPanel;
  index: number;
  isOpen: boolean;
  onOpen: (id: string) => void;
}

/**
 * One panel. Extracted so its click handler is a stable reference rather than a
 * closure rebuilt for every panel on every render.
 */
function Panel({ panel, index, isOpen, onOpen }: PanelProps) {
  const handleClick = useCallback(() => {
    onOpen(panel.id);
  }, [onOpen, panel.id]);

  return (
    <li className={`${styles.panel} ${isOpen ? styles.panelOpen : ''}`}>
      <h3>
        <button
          type="button"
          className={styles.trigger}
          aria-expanded={isOpen}
          aria-controls={`panel-content-${panel.id}`}
          id={`panel-trigger-${panel.id}`}
          onClick={handleClick}
        >
          <span className={styles.ordinal} aria-hidden="true">
            {String(index + 1).padStart(2, '0')}
          </span>
          <span className={styles.name}>{panel.name}</span>
          {isOpen && <span className={styles.headline}>{panel.headline}</span>}
          <PlusIcon />
        </button>
      </h3>

      {isOpen && (
        <section
          className={styles.content}
          id={`panel-content-${panel.id}`}
          aria-labelledby={`panel-trigger-${panel.id}`}
        >
          <p className={styles.body}>{panel.body}</p>
          <p className={styles.outcome}>
            <span aria-hidden="true">→</span>
            {panel.outcome}
          </p>
        </section>
      )}
    </li>
  );
}

/**
 * Accordion where exactly one panel is open at a time.
 *
 * Single-open rather than multi-open because these describe one continuous
 * workflow: reading them side by side would invite comparison, where the point
 * is that each step leads into the next.
 */
export function ExpandingPanels({ panels }: { panels: readonly ExpandingPanel[] }) {
  const [openId, setOpenId] = useState(panels[0]?.id ?? '');

  return (
    <ul className={styles.panels}>
      {panels.map((panel, index) => (
        <Panel
          key={panel.id}
          panel={panel}
          index={index}
          isOpen={panel.id === openId}
          onOpen={setOpenId}
        />
      ))}
    </ul>
  );
}

function PlusIcon() {
  return (
    <svg
      className={styles.marker}
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
