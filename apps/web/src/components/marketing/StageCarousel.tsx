import { useCallback, useRef, useState, type KeyboardEvent } from 'react';

import styles from './StageCarousel.module.css';

export interface CarouselStage {
  /** Stable identifier, also the image basename. */
  id: string;
  name: string;
  /** One-line summary shown beside the image. */
  summary: string;
  /** The constraint or guarantee that makes this stage trustworthy. */
  detail: string;
  /** Describes the artwork itself, not the stage it illustrates. */
  imageAlt: string;
}

interface StageCarouselProps {
  stages: readonly CarouselStage[];
  /** Names the tablist for assistive technology. */
  label: string;
}

interface StageTabProps {
  stage: CarouselStage;
  index: number;
  isSelected: boolean;
  onSelect: (index: number) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}

/**
 * One tab. Extracted so its click handler can be a stable reference rather than
 * a closure rebuilt for every tab on every render of the carousel.
 */
function StageTab({ stage, index, isSelected, onSelect, onKeyDown }: StageTabProps) {
  const handleClick = useCallback(() => {
    onSelect(index);
  }, [onSelect, index]);

  return (
    <button
      type="button"
      role="tab"
      id={`stage-tab-${stage.id}`}
      aria-selected={isSelected}
      aria-controls={`stage-panel-${stage.id}`}
      tabIndex={isSelected ? 0 : -1}
      className={`${styles.tab} ${isSelected ? styles.tabSelected : ''}`}
      onClick={handleClick}
      onKeyDown={onKeyDown}
    >
      <span className={styles.tabIndex}>{String(index + 1).padStart(2, '0')}</span>
      {stage.name}
    </button>
  );
}

/**
 * Tabbed carousel through an ordered sequence of stages.
 *
 * Implements the ARIA tabs pattern with a roving tabindex: only the selected tab
 * is in the tab order, and arrow keys move between tabs while Home and End jump
 * to the ends.
 *
 * There is no auto-advance. A carousel that moves on its own competes with the
 * reader for control and is a well-documented accessibility problem.
 */
export function StageCarousel({ stages, label }: StageCarouselProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const tabsRef = useRef<HTMLDivElement>(null);

  const selectAndFocus = useCallback((index: number): void => {
    setSelectedIndex(index);
    // Focus follows selection so the reader is not left on a tab that is no
    // longer current. Queried from the container rather than tracked in a ref
    // array, which would need a new callback ref for every tab.
    const tabs = tabsRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    tabs?.[index]?.focus();
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>): void => {
      const lastIndex = stages.length - 1;
      const nextIndex = {
        ArrowRight: selectedIndex === lastIndex ? 0 : selectedIndex + 1,
        ArrowLeft: selectedIndex === 0 ? lastIndex : selectedIndex - 1,
        Home: 0,
        End: lastIndex,
      }[event.key];

      if (nextIndex === undefined) {
        return;
      }

      event.preventDefault();
      selectAndFocus(nextIndex);
    },
    [selectedIndex, stages.length, selectAndFocus],
  );

  const goPrevious = useCallback((): void => {
    setSelectedIndex((current) => Math.max(0, current - 1));
  }, []);

  const goNext = useCallback((): void => {
    setSelectedIndex((current) => Math.min(stages.length - 1, current + 1));
  }, [stages.length]);

  const selected = stages[selectedIndex];
  if (selected === undefined) {
    return null;
  }

  return (
    <div className={styles.carousel}>
      <div className={styles.tabs} role="tablist" aria-label={label} ref={tabsRef}>
        {stages.map((stage, index) => (
          <StageTab
            key={stage.id}
            stage={stage}
            index={index}
            isSelected={index === selectedIndex}
            onSelect={setSelectedIndex}
            onKeyDown={handleKeyDown}
          />
        ))}
      </div>

      <div
        className={styles.panel}
        role="tabpanel"
        id={`stage-panel-${selected.id}`}
        aria-labelledby={`stage-tab-${selected.id}`}
        tabIndex={0}
      >
        <figure className={styles.figure}>
          {/* Keyed on id so the settle animation replays when the stage changes. */}
          <img
            key={selected.id}
            className={styles.image}
            src={`/media/stages/${selected.id}.webp`}
            alt={selected.imageAlt}
            width={1200}
            height={800}
            loading="lazy"
            decoding="async"
          />
          <span className={styles.figureWash} aria-hidden="true" />
        </figure>

        <div className={styles.body}>
          <p className={styles.stageOrdinal}>
            Stage {selectedIndex + 1} of {stages.length}
          </p>
          <h3 className={styles.stageName}>{selected.name}</h3>
          <p className={styles.stageBody}>{selected.summary}</p>
          <p className={styles.stageDetail}>{selected.detail}</p>
        </div>
      </div>

      <div className={styles.controls}>
        <button
          type="button"
          className={styles.control}
          onClick={goPrevious}
          disabled={selectedIndex === 0}
          aria-label="Previous stage"
        >
          <ChevronIcon direction="left" />
        </button>
        <button
          type="button"
          className={styles.control}
          onClick={goNext}
          disabled={selectedIndex === stages.length - 1}
          aria-label="Next stage"
        >
          <ChevronIcon direction="right" />
        </button>
        <p className={styles.position} aria-hidden="true">
          {String(selectedIndex + 1).padStart(2, '0')} / {String(stages.length).padStart(2, '0')}
        </p>
      </div>
    </div>
  );
}

function ChevronIcon({ direction }: { direction: 'left' | 'right' }) {
  const path = direction === 'left' ? 'M12 4L6 10l6 6' : 'M8 4l6 6-6 6';
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d={path} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
