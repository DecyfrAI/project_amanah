import { useCallback, useState } from 'react';

import { ROOM_LEAD, ROOM_VANTAGES, type RoomVantage } from './lesson-activities';

import styles from './LessonActivity.module.css';

/**
 * In-the-room vs outside-the-room cues for module 04. Reflection only, no score.
 */
export function LessonRoomActivity() {
  const [vantage, setVantage] = useState<RoomVantage | undefined>(undefined);
  const selected = ROOM_VANTAGES.find((entry) => entry.id === vantage);

  return (
    <div className={styles.activity} data-lesson-activity="room">
      <p className={styles.lead}>{ROOM_LEAD}</p>
      <fieldset className={styles.block}>
        <legend className={styles.prompt}>Vantage</legend>
        <div className={styles.optionGrid}>
          {ROOM_VANTAGES.map((entry) => (
            <VantageButton
              key={entry.id}
              id={entry.id}
              label={entry.label}
              selected={vantage === entry.id}
              onSelect={setVantage}
            />
          ))}
        </div>
      </fieldset>
      {selected !== undefined ? (
        <div className={styles.block}>
          <ul className={styles.cues}>
            {selected.cues.map((cue) => (
              <li key={cue}>{cue}</li>
            ))}
          </ul>
          <p className={styles.reflection}>{selected.reflection}</p>
        </div>
      ) : null}
    </div>
  );
}

function VantageButton({
  id,
  label,
  selected,
  onSelect,
}: {
  id: RoomVantage;
  label: string;
  selected: boolean;
  onSelect: (id: RoomVantage) => void;
}) {
  const handleClick = useCallback((): void => {
    onSelect(id);
  }, [id, onSelect]);

  return (
    <button
      type="button"
      className={selected ? `${styles.option} ${styles.optionSelected}` : styles.option}
      aria-pressed={selected}
      onClick={handleClick}
    >
      {label}
    </button>
  );
}
