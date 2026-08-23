import { useCallback, useState } from 'react';

import { MINDSET_STAGES } from '@/components/marketing/mindset-stages';

import { ActivityFeedback, ActivityOption } from './lesson-activity-ui';
import { STAGE_LEAD, STAGE_REMARKS } from './lesson-activities';

import styles from './LessonActivity.module.css';

/**
 * “Which stage is this remark?” for module 03, beside the Borum figure.
 */
export function LessonStageActivity() {
  return (
    <div className={styles.activity} data-lesson-activity="stage">
      <p className={styles.lead}>{STAGE_LEAD}</p>
      {STAGE_REMARKS.map((item) => (
        <RemarkBlock key={item.id} item={item} />
      ))}
    </div>
  );
}

function RemarkBlock({ item }: { item: (typeof STAGE_REMARKS)[number] }) {
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const revealed = selectedId !== undefined;
  const fits = selectedId === item.stageId;

  const handleSelect = useCallback((stageId: string): void => {
    setSelectedId((current) => current ?? stageId);
  }, []);

  return (
    <fieldset className={styles.block}>
      <legend className={styles.itemStatement}>{item.remark}</legend>
      <div className={styles.optionGrid}>
        {MINDSET_STAGES.map((stage) => (
          <StageOption
            key={stage.id}
            stageId={stage.id}
            label={`${stage.number} ${stage.name}`}
            selected={selectedId === stage.id}
            revealed={revealed}
            correct={item.stageId === stage.id}
            onSelect={handleSelect}
          />
        ))}
      </div>
      {revealed ? (
        <ActivityFeedback
          indicator={fits ? 'ok' : 'degraded'}
          label={fits ? 'Closest stage' : 'Other stage'}
        >
          {item.explanation}
        </ActivityFeedback>
      ) : null}
    </fieldset>
  );
}

function StageOption({
  stageId,
  label,
  selected,
  revealed,
  correct,
  onSelect,
}: {
  stageId: string;
  label: string;
  selected: boolean;
  revealed: boolean;
  correct: boolean;
  onSelect: (id: string) => void;
}) {
  const handleClick = useCallback((): void => {
    onSelect(stageId);
  }, [onSelect, stageId]);

  return (
    <ActivityOption
      label={label}
      selected={selected}
      revealed={revealed}
      correct={correct}
      locked={revealed}
      onSelect={handleClick}
    />
  );
}
