import type { ReactNode } from 'react';

import { StatusPill, type StatusIndicator } from '@/components/ui/StatusPill';

import styles from './LessonActivity.module.css';

interface ActivityFeedbackProps {
  indicator: StatusIndicator;
  label: string;
  children: ReactNode;
}

export function ActivityFeedback({ indicator, label, children }: ActivityFeedbackProps) {
  return (
    <output className={styles.feedback}>
      <StatusPill indicator={indicator} label={label} />
      <span className={styles.feedbackBody}>{children}</span>
    </output>
  );
}

interface ActivityOptionProps {
  label: string;
  selected: boolean;
  revealed: boolean;
  correct: boolean;
  locked: boolean;
  wide?: boolean;
  onSelect: () => void;
}

export function ActivityOption({
  label,
  selected,
  revealed,
  correct,
  locked,
  wide = false,
  onSelect,
}: ActivityOptionProps) {
  const className = optionClassName(selected, revealed, correct, wide);
  const mark = optionMark(selected, revealed, correct);

  return (
    <button
      type="button"
      className={className}
      aria-pressed={selected}
      disabled={locked && !selected}
      onClick={onSelect}
    >
      {mark !== undefined ? <span className={styles.mark}>{mark}</span> : null}
      {label}
    </button>
  );
}

function optionClassName(
  selected: boolean,
  revealed: boolean,
  correct: boolean,
  wide: boolean,
): string {
  const classes = [styles.option];
  if (wide) {
    classes.push(styles.wideOption);
  }
  if (revealed && correct) {
    classes.push(styles.optionCorrect);
    return classes.join(' ');
  }
  if (revealed && selected && !correct) {
    classes.push(styles.optionIncorrect);
    return classes.join(' ');
  }
  if (selected) {
    classes.push(styles.optionSelected);
  }
  return classes.join(' ');
}

function optionMark(selected: boolean, revealed: boolean, correct: boolean): string | undefined {
  if (!revealed) {
    return undefined;
  }
  if (correct) {
    return 'Fits';
  }
  if (selected) {
    return 'Not this claim';
  }
  return undefined;
}
