import { useCallback, useState } from 'react';

import { ActivityFeedback, ActivityOption } from './lesson-activity-ui';
import { PYRAMID_LABELS, SORT_ITEMS, SORT_LEAD, type PyramidBucket } from './lesson-activities';

import styles from './LessonActivity.module.css';

type PyramidPicks = Partial<Record<string, PyramidBucket>>;

/**
 * Two-column sort for module 01: opinion pyramid vs action pyramid.
 */
export function LessonSortActivity() {
  const [picks, setPicks] = useState<PyramidPicks>({});

  return (
    <div className={styles.activity} data-lesson-activity="sort">
      <p className={styles.lead}>{SORT_LEAD}</p>
      {SORT_ITEMS.map((item) => (
        <SortItem
          key={item.id}
          id={item.id}
          statement={item.statement}
          bucket={item.bucket}
          explanation={item.explanation}
          pick={picks[item.id]}
          onPick={setPicks}
        />
      ))}
    </div>
  );
}

function SortItem({
  id,
  statement,
  bucket,
  explanation,
  pick,
  onPick,
}: {
  id: string;
  statement: string;
  bucket: PyramidBucket;
  explanation: string;
  pick: PyramidBucket | undefined;
  onPick: (update: (current: PyramidPicks) => PyramidPicks) => void;
}) {
  const revealed = pick !== undefined;
  const fits = pick === bucket;

  const handleOpinion = useCallback((): void => {
    onPick((current) => (current[id] === undefined ? { ...current, [id]: 'opinion' } : current));
  }, [id, onPick]);

  const handleAction = useCallback((): void => {
    onPick((current) => (current[id] === undefined ? { ...current, [id]: 'action' } : current));
  }, [id, onPick]);

  return (
    <fieldset className={styles.block}>
      <legend className={styles.itemStatement}>{statement}</legend>
      <div className={styles.optionGrid}>
        <ActivityOption
          label={PYRAMID_LABELS.opinion}
          selected={pick === 'opinion'}
          revealed={revealed}
          correct={bucket === 'opinion'}
          locked={revealed}
          onSelect={handleOpinion}
        />
        <ActivityOption
          label={PYRAMID_LABELS.action}
          selected={pick === 'action'}
          revealed={revealed}
          correct={bucket === 'action'}
          locked={revealed}
          onSelect={handleAction}
        />
      </div>
      {revealed ? (
        <ActivityFeedback
          indicator={fits ? 'ok' : 'degraded'}
          label={fits ? 'Fits the distinction' : 'Other pyramid'}
        >
          {explanation}
        </ActivityFeedback>
      ) : null}
    </fieldset>
  );
}
