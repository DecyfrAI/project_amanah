import { useCallback, useState, type ReactNode } from 'react';

import { ActivityFeedback, ActivityOption } from './lesson-activity-ui';
import type { ChoiceActivityDef, ChoiceOption, ChoiceQuestion } from './lesson-activities';

import styles from './LessonActivity.module.css';

interface LessonChoiceActivityProps {
  activity: ChoiceActivityDef;
}

/**
 * Multiple-choice exercise used by modules 02, 05, 07, and 08.
 */
export function LessonChoiceActivity({ activity }: LessonChoiceActivityProps) {
  return (
    <div className={styles.activity} data-lesson-activity="choice">
      <p className={styles.lead}>{activity.lead}</p>
      {activity.table !== undefined ? <ScopedTable table={activity.table} /> : null}
      {activity.questions.map((question) => (
        <QuestionBlock key={question.id} question={question} reveal={activity.reveal} />
      ))}
    </div>
  );
}

function QuestionBlock({
  question,
  reveal,
}: {
  question: ChoiceQuestion;
  reveal: ChoiceActivityDef['reveal'];
}) {
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const selected = question.options.find((option) => option.id === selectedId);
  const locked = reveal === 'lock' && selectedId !== undefined;

  const handleSelect = useCallback(
    (optionId: string): void => {
      setSelectedId((current) => {
        if (reveal === 'lock' && current !== undefined) {
          return current;
        }
        return optionId;
      });
    },
    [reveal],
  );

  return (
    <fieldset className={styles.block}>
      <legend className={styles.prompt}>{question.prompt}</legend>
      <div className={styles.optionGrid}>
        {question.options.map((option) => (
          <OptionButton
            key={option.id}
            option={option}
            selected={selectedId === option.id}
            revealed={reveal === 'inspect' ? selectedId === option.id : selectedId !== undefined}
            locked={locked}
            wide={option.label.length > 80}
            onSelect={handleSelect}
          />
        ))}
      </div>
      {selected !== undefined ? (
        <ActivityFeedback
          indicator={selected.correct ? 'ok' : 'degraded'}
          label={selected.correct ? 'Supported' : 'Not this claim'}
        >
          {selected.explanation}
        </ActivityFeedback>
      ) : null}
    </fieldset>
  );
}

function OptionButton({
  option,
  selected,
  revealed,
  locked,
  wide,
  onSelect,
}: {
  option: ChoiceOption;
  selected: boolean;
  revealed: boolean;
  locked: boolean;
  wide: boolean;
  onSelect: (id: string) => void;
}) {
  const handleClick = useCallback((): void => {
    onSelect(option.id);
  }, [onSelect, option.id]);

  return (
    <ActivityOption
      label={option.label}
      selected={selected}
      revealed={revealed}
      correct={option.correct}
      locked={locked}
      wide={wide}
      onSelect={handleClick}
    />
  );
}

function ScopedTable({ table }: { table: NonNullable<ChoiceActivityDef['table']> }) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <caption>{table.caption}</caption>
        <thead>
          <tr>
            <th scope="col">Window</th>
            <th scope="col">Classified as likely</th>
            <th scope="col">Comments collected</th>
            <th scope="col">Coverage</th>
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.id}>
              <th scope="row">{row.window}</th>
              <GapCell isGap={row.isGap}>{row.labelled}</GapCell>
              <GapCell isGap={row.isGap}>{row.collected}</GapCell>
              <GapCell isGap={row.isGap}>{row.coverage}</GapCell>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GapCell({ isGap, children }: { isGap: boolean; children: ReactNode }) {
  return <td className={isGap ? styles.gapCell : undefined}>{children}</td>;
}
