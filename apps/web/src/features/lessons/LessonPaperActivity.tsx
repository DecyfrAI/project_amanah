import { useCallback, useState } from 'react';

import { ActivityFeedback, ActivityOption } from './lesson-activity-ui';
import { PAPER_LEAD, PAPER_ROUNDS, type PaperRound } from './lesson-activities';

import styles from './LessonActivity.module.css';

/**
 * Two-card “found vs did not” for module 06 (Ribeiro vs later YouTube work).
 */
export function LessonPaperActivity() {
  return (
    <div className={styles.activity} data-lesson-activity="paper">
      <p className={styles.lead}>{PAPER_LEAD}</p>
      {PAPER_ROUNDS.map((round) => (
        <PaperRoundBlock key={round.id} round={round} />
      ))}
    </div>
  );
}

function PaperRoundBlock({ round }: { round: PaperRound }) {
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const cards = [round.found, round.overclaim];
  const selected = cards.find((card) => card.id === selectedId);
  const revealed = selectedId !== undefined;

  const handleSelect = useCallback((cardId: string): void => {
    setSelectedId((current) => current ?? cardId);
  }, []);

  return (
    <fieldset className={styles.block}>
      <legend className={styles.prompt}>{round.prompt}</legend>
      <p className={styles.paper}>{round.paper}</p>
      <div className={styles.optionGrid}>
        {cards.map((card) => (
          <PaperCardButton
            key={card.id}
            cardId={card.id}
            label={card.label}
            selected={selectedId === card.id}
            revealed={revealed}
            correct={card.id === round.found.id}
            onSelect={handleSelect}
          />
        ))}
      </div>
      {selected !== undefined ? (
        <ActivityFeedback
          indicator={selected.id === round.found.id ? 'ok' : 'degraded'}
          label={selected.id === round.found.id ? 'What the paper found' : 'What it did not'}
        >
          {selected.explanation}
        </ActivityFeedback>
      ) : null}
    </fieldset>
  );
}

function PaperCardButton({
  cardId,
  label,
  selected,
  revealed,
  correct,
  onSelect,
}: {
  cardId: string;
  label: string;
  selected: boolean;
  revealed: boolean;
  correct: boolean;
  onSelect: (id: string) => void;
}) {
  const handleClick = useCallback((): void => {
    onSelect(cardId);
  }, [cardId, onSelect]);

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
