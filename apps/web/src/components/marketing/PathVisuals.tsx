import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
} from 'react';

import { useReducedMotion } from '@/hooks/useReducedMotion';

import { MindsetStages } from './MindsetStages';

import styles from './PathVisuals.module.css';

const VIEWS = [
  { id: 'room', name: 'The room' },
  { id: 'model', name: 'The model' },
] as const;

type ViewId = (typeof VIEWS)[number]['id'];

export const ROOM_SLIDES = [
  {
    id: 'isolation',
    title: 'Isolation',
    line: 'A silhouette at a glowing screen. The face is not visible.',
    src: '/media/path-room-screen.webp',
    alt: 'The room: silhouette of a person facing a bright screen in a dark room. The face is not visible.',
  },
  {
    id: 'empty-chair',
    title: 'An empty chair',
    line: 'The session can stay on after the person has left.',
    src: '/media/path-empty-chair.webp',
    alt: 'An empty chair at a dark desk. A monitor glows with no readable interface.',
  },
  {
    id: 'night-feed',
    title: 'The night feed',
    line: 'A phone put down still receives the next post.',
    src: '/media/path-phone-night.webp',
    alt: 'A hand holds a phone in a dark room, seen from behind. No face is visible.',
  },
  {
    id: 'narrower-doors',
    title: 'Narrower doors',
    line: 'Rooms get smaller as the path continues.',
    src: '/media/path-narrow-doors.webp',
    alt: 'A narrow corridor of many closed doors receding into darkness. No people are in the frame.',
  },
  {
    id: 'wall-moves-on',
    title: 'The wall that moves on',
    line: 'Comments stack and scroll. No one stays to answer.',
    src: '/media/path-comment-wall.webp',
    alt: 'A soft-focus wall of abstract comment bars on a dark screen. No words are readable.',
  },
  {
    id: 'lit-window',
    title: 'One lit window',
    line: 'Isolation can look like an ordinary night.',
    src: '/media/path-lit-window.webp',
    alt: 'A distant building at night with a single lit room. No people are visible.',
  },
] as const;

/** Milliseconds each still is held. Keep in step with `--duration-path-cycle`. */
export const PATH_CYCLE_MS = 7000;

/**
 * Path section visuals: a photo carousel of the online room, then Borum's
 * four-stage model. Autoplay is only for the stills. The model is clicked.
 */
export function PathVisuals() {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const tabsRef = useRef<HTMLDivElement>(null);
  const selected = VIEWS[selectedIndex] ?? VIEWS[0];

  const selectAndFocus = useCallback((index: number): void => {
    setSelectedIndex(index);
    const tabs = tabsRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    tabs?.[index]?.focus();
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>): void => {
      const lastIndex = VIEWS.length - 1;
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
    [selectAndFocus, selectedIndex],
  );

  return (
    <div className={styles.visuals}>
      <div className={styles.tabs} role="tablist" aria-label="Path illustrations" ref={tabsRef}>
        {VIEWS.map((view, index) => (
          <ViewTab
            key={view.id}
            id={view.id}
            name={view.name}
            isSelected={index === selectedIndex}
            index={index}
            onSelect={setSelectedIndex}
            onKeyDown={handleKeyDown}
          />
        ))}
      </div>

      <div
        className={styles.panel}
        role="tabpanel"
        id={`path-panel-${selected.id}`}
        aria-labelledby={`path-tab-${selected.id}`}
        tabIndex={0}
      >
        {selected.id === 'room' ? <RoomCarousel /> : <MindsetStages />}
      </div>
    </div>
  );
}

interface ViewTabProps {
  id: ViewId;
  name: string;
  isSelected: boolean;
  index: number;
  onSelect: (index: number) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}

function ViewTab({ id, name, isSelected, index, onSelect, onKeyDown }: ViewTabProps) {
  const handleClick = useCallback((): void => {
    onSelect(index);
  }, [index, onSelect]);

  return (
    <button
      type="button"
      role="tab"
      id={`path-tab-${id}`}
      aria-selected={isSelected}
      aria-controls={`path-panel-${id}`}
      tabIndex={isSelected ? 0 : -1}
      className={isSelected ? `${styles.tab} ${styles.tabSelected}` : styles.tab}
      onClick={handleClick}
      onKeyDown={onKeyDown}
    >
      {name}
    </button>
  );
}

function RoomCarousel() {
  const prefersReducedMotion = useReducedMotion();
  const carouselRef = useRef<HTMLElement>(null);
  const [slideIndex, setSlideIndex] = useState(0);
  const [userPaused, setUserPaused] = useState(false);
  const [hoverPaused, setHoverPaused] = useState(false);
  const [focusPaused, setFocusPaused] = useState(false);

  const isPlaying = !prefersReducedMotion && !userPaused && !hoverPaused && !focusPaused;
  const selected = ROOM_SLIDES[slideIndex] ?? ROOM_SLIDES[0];

  useEffect(() => {
    if (!isPlaying) {
      return;
    }

    const timer = window.setInterval(() => {
      setSlideIndex((current) => (current + 1) % ROOM_SLIDES.length);
    }, PATH_CYCLE_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [isPlaying]);

  useEffect(() => {
    const node = carouselRef.current;
    if (node === null) {
      return;
    }

    const pause = (): void => {
      setHoverPaused(true);
    };
    const resume = (): void => {
      setHoverPaused(false);
    };

    node.addEventListener('mouseenter', pause);
    node.addEventListener('mouseleave', resume);
    return () => {
      node.removeEventListener('mouseenter', pause);
      node.removeEventListener('mouseleave', resume);
    };
  }, []);

  const showSlide = useCallback((index: number): void => {
    setSlideIndex((index + ROOM_SLIDES.length) % ROOM_SLIDES.length);
  }, []);

  const handlePrevious = useCallback((): void => {
    showSlide(slideIndex - 1);
  }, [showSlide, slideIndex]);

  const handleNext = useCallback((): void => {
    showSlide(slideIndex + 1);
  }, [showSlide, slideIndex]);

  const handleTogglePlayback = useCallback((): void => {
    setUserPaused((current) => !current);
  }, []);

  const handleFocusCapture = useCallback((event: FocusEvent<HTMLElement>): void => {
    if (event.target instanceof HTMLElement && event.target.matches(':focus-visible')) {
      setFocusPaused(true);
    }
  }, []);

  const handleBlurCapture = useCallback((event: FocusEvent<HTMLElement>): void => {
    const next = event.relatedTarget;
    if (next instanceof Node && event.currentTarget.contains(next)) {
      return;
    }
    setFocusPaused(false);
  }, []);

  if (selected === undefined) {
    return null;
  }

  return (
    <section
      ref={carouselRef}
      className={styles.carousel}
      aria-roledescription="carousel"
      aria-label="The room online"
      onFocusCapture={handleFocusCapture}
      onBlurCapture={handleBlurCapture}
    >
      <figure className={styles.room}>
        <img
          key={selected.id}
          className={styles.image}
          src={selected.src}
          alt={selected.alt}
          width={1536}
          height={1024}
          decoding="async"
        />
        <figcaption className={styles.caption} aria-live={isPlaying ? 'off' : 'polite'}>
          <p className={styles.title}>{selected.title}</p>
          <p className={styles.line}>{selected.line}</p>
        </figcaption>
      </figure>

      <div className={styles.controls}>
        <button
          type="button"
          className={styles.control}
          onClick={handlePrevious}
          aria-label="Previous still"
        >
          <ChevronIcon direction="left" />
        </button>
        {prefersReducedMotion ? null : (
          <button type="button" className={styles.playback} onClick={handleTogglePlayback}>
            {userPaused ? 'Play' : 'Pause'}
          </button>
        )}
        <button
          type="button"
          className={styles.control}
          onClick={handleNext}
          aria-label="Next still"
        >
          <ChevronIcon direction="right" />
        </button>
        <p className={styles.position} aria-hidden="true">
          {String(slideIndex + 1).padStart(2, '0')} / {String(ROOM_SLIDES.length).padStart(2, '0')}
        </p>
      </div>

      <fieldset className={styles.dots}>
        <legend className="visually-hidden">Choose a still</legend>
        {ROOM_SLIDES.map((slide, index) => (
          <DotButton
            key={slide.id}
            title={slide.title}
            isSelected={index === slideIndex}
            index={index}
            onSelect={showSlide}
          />
        ))}
      </fieldset>
    </section>
  );
}

interface DotButtonProps {
  title: string;
  isSelected: boolean;
  index: number;
  onSelect: (index: number) => void;
}

function DotButton({ title, isSelected, index, onSelect }: DotButtonProps) {
  const handleClick = useCallback((): void => {
    onSelect(index);
  }, [index, onSelect]);

  return (
    <button
      type="button"
      className={styles.dotButton}
      aria-label={title}
      aria-current={isSelected ? 'true' : undefined}
      onClick={handleClick}
    >
      <span className={isSelected ? `${styles.dot} ${styles.dotSelected}` : styles.dot} />
    </button>
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
