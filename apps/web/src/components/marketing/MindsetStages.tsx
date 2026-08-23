import { useCallback, useState } from 'react';

import { MINDSET_CITATION, MINDSET_STAGES } from './mindset-stages';

import styles from './MindsetStages.module.css';

interface MindsetStagesProps {
  /** Names the figure when more than one appears on a page. */
  labelledBy?: string;
}

/**
 * Interactive four-stage model from Borum 2003.
 *
 * Stages are buttons so a reader can sit with one at a time. Colour darkens
 * along the sequence, but each stage also has a number, a name, and a quote.
 */
export function MindsetStages({ labelledBy }: MindsetStagesProps) {
  const firstStage = MINDSET_STAGES[0];
  const [selectedId, setSelectedId] = useState(firstStage?.id ?? 'grievance');
  const selected = MINDSET_STAGES.find((stage) => stage.id === selectedId) ?? firstStage;

  if (selected === undefined) {
    return null;
  }

  return (
    <figure className={styles.figure} aria-labelledby={labelledBy}>
      <figcaption className={styles.caption}>
        <p className={styles.kicker}>A published model</p>
        <p className={styles.title}>Four stages toward devaluing a target</p>
      </figcaption>

      <ol className={styles.stages}>
        {MINDSET_STAGES.map((stage, index) => (
          <StageButton
            key={stage.id}
            id={stage.id}
            number={stage.number}
            name={stage.name}
            quote={stage.quote}
            isSelected={stage.id === selectedId}
            depth={index}
            onSelect={setSelectedId}
          />
        ))}
      </ol>

      <p className={styles.detail}>
        <span className={styles.detailQuote}>{selected.quote}.</span> {selected.summary}
      </p>

      <p className={styles.cite}>
        Source:{' '}
        <a className={styles.link} href={MINDSET_CITATION.href} rel="noreferrer" target="_blank">
          {MINDSET_CITATION.label} (opens in a new tab)
        </a>
        . This model describes some pathways. It does not describe every poster, and it does not
        claim a comment caused violence.
      </p>
    </figure>
  );
}

interface StageButtonProps {
  id: string;
  number: string;
  name: string;
  quote: string;
  isSelected: boolean;
  depth: number;
  onSelect: (id: string) => void;
}

function StageButton({ id, number, name, quote, isSelected, depth, onSelect }: StageButtonProps) {
  const handleClick = useCallback((): void => {
    onSelect(id);
  }, [id, onSelect]);

  return (
    <li className={styles.stage} data-depth={depth} data-selected={isSelected ? 'true' : 'false'}>
      <button
        type="button"
        className={styles.stageButton}
        aria-pressed={isSelected}
        onClick={handleClick}
      >
        <span className={styles.stageNumber}>{number}</span>
        <span className={styles.stageCopy}>
          <span className={styles.stageName}>{name}</span>
          <span className={styles.stageQuote}>{quote}</span>
        </span>
      </button>
    </li>
  );
}
