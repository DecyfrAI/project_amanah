import { useCallback } from 'react';

import type { PostReactions, ReactionKind } from '@/api/contracts';

import styles from './ReactionBar.module.css';

interface ReactionBarProps {
  reactions: PostReactions;
  disabled: boolean;
  onReact: (kind: ReactionKind) => void;
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ContextIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 7v4M8 5.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function ReactionBar({ reactions, disabled, onReact }: ReactionBarProps) {
  const handleUseful = useCallback((): void => {
    onReact('useful');
  }, [onReact]);

  const handleNeedsContext = useCallback((): void => {
    onReact('needs_context');
  }, [onReact]);

  return (
    <div className={styles.bar}>
      <button
        type="button"
        className={styles.reaction}
        aria-pressed={reactions.viewer === 'useful'}
        disabled={disabled}
        onClick={handleUseful}
      >
        <CheckIcon />
        Useful
        <span className={styles.count}>{reactions.useful}</span>
      </button>
      <button
        type="button"
        className={styles.reaction}
        aria-pressed={reactions.viewer === 'needs_context'}
        disabled={disabled}
        onClick={handleNeedsContext}
      >
        <ContextIcon />
        Needs context
        <span className={styles.count}>{reactions.needs_context}</span>
      </button>
    </div>
  );
}
