import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { MindsetStages } from '@/components/marketing/MindsetStages';

import { LessonActivity } from './LessonActivity';
import {
  externalLinkProps,
  LESSON_CASE_NOTE,
  LESSON_RESEARCH_NOTE,
  lessonReaderPages,
  sourceOutboundHref,
  type LessonMedia,
  type LessonModule,
  type LessonReaderPage,
  type LessonSource,
} from './lesson-copy';

import styles from './LessonReader.module.css';

interface LessonReaderProps {
  module: LessonModule;
  catalogTo: string;
}

/**
 * Book-like reader: one chapter at a time, Sources last, keyboard arrows.
 * Pages do not auto-advance.
 */
export function LessonReader({ module, catalogTo }: LessonReaderProps) {
  const pages = useMemo(() => lessonReaderPages(module), [module]);
  const pageCount = pages.length;
  const [pageIndex, setPageIndex] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const goTo = useCallback(
    (nextIndex: number): void => {
      setPageIndex((current) => {
        const next = Math.min(Math.max(nextIndex, 0), pageCount - 1);
        return next === current ? current : next;
      });
      queueMicrotask(() => {
        headingRef.current?.focus();
      });
    },
    [pageCount],
  );

  const goPrevious = useCallback((): void => {
    setPageIndex((current) => Math.max(current - 1, 0));
    queueMicrotask(() => {
      headingRef.current?.focus();
    });
  }, []);

  const goNext = useCallback((): void => {
    setPageIndex((current) => Math.min(current + 1, pageCount - 1));
    queueMicrotask(() => {
      headingRef.current?.focus();
    });
  }, [pageCount]);

  useEffect(() => {
    function handleKey(event: KeyboardEvent): void {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) {
        return;
      }
      if (isTypingTarget(event.target) || isInsideActivity(event.target)) {
        return;
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        goNext();
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        goPrevious();
      }
    }

    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
    };
  }, [goNext, goPrevious]);

  const page = pages[pageIndex];
  if (page === undefined) {
    return null;
  }

  const pageLabel = `Page ${pageIndex + 1} of ${pages.length}`;
  const isCase = module.track === 'case';
  const kicker = isCase ? `Case study · ${pageLabel}` : `Module ${module.number} · ${pageLabel}`;

  return (
    <article className={styles.reader}>
      <p className={styles.kicker}>{kicker}</p>
      <h1 className={styles.title}>{module.title}</h1>
      <p className={styles.thesis}>{module.thesis}</p>
      <p className={styles.researchNote}>{isCase ? LESSON_CASE_NOTE : LESSON_RESEARCH_NOTE}</p>

      <progress
        className={styles.progress}
        max={pageCount}
        value={pageIndex + 1}
        aria-label={`${pageLabel}: ${page.title}`}
      >
        {pageLabel}
      </progress>

      <div className={styles.layout}>
        <nav className={styles.contents} aria-label="Chapters">
          <ol className={styles.contentsList}>
            {pages.map((entry, index) => (
              <ContentsItem
                key={entry.id}
                title={entry.title}
                index={index}
                isCurrent={index === pageIndex}
                onSelect={goTo}
              />
            ))}
          </ol>
        </nav>

        <section className={styles.page} aria-labelledby="lesson-page-title">
          <h2 id="lesson-page-title" className={styles.pageTitle} tabIndex={-1} ref={headingRef}>
            {page.title}
          </h2>
          {page.kind === 'sources' ? (
            <SourcesList sources={module.sources} />
          ) : page.kind === 'activity' ? (
            <LessonActivity moduleId={module.id} />
          ) : (
            <ChapterBody page={page} labelledBy="lesson-page-title" />
          )}
        </section>
      </div>

      <nav className={styles.pager} aria-label="Page">
        <button
          type="button"
          className={styles.pagerButton}
          onClick={goPrevious}
          disabled={pageIndex === 0}
        >
          Previous page
        </button>
        <button
          type="button"
          className={styles.pagerButton}
          onClick={goNext}
          disabled={pageIndex === pages.length - 1}
        >
          Next page
        </button>
      </nav>

      <p className={styles.back}>
        <Link to={catalogTo}>Back to Lessons</Link>
      </p>
    </article>
  );
}

function ContentsItem({
  title,
  index,
  isCurrent,
  onSelect,
}: {
  title: string;
  index: number;
  isCurrent: boolean;
  onSelect: (index: number) => void;
}) {
  const handleClick = useCallback((): void => {
    onSelect(index);
  }, [index, onSelect]);

  return (
    <li>
      <button
        type="button"
        className={styles.contentsButton}
        aria-current={isCurrent ? 'page' : undefined}
        onClick={handleClick}
      >
        {title}
      </button>
    </li>
  );
}

function ChapterBody({ page, labelledBy }: { page: LessonReaderPage; labelledBy: string }) {
  return (
    <>
      {page.paragraphs.map((paragraph) => (
        <p key={paragraph} className={styles.body}>
          {paragraph}
        </p>
      ))}
      {page.visual === 'mindset-stages' ? <MindsetStages labelledBy={labelledBy} /> : null}
      {page.visual === 'isolation-room' ? <IsolationRoomFigure /> : null}
      {page.visual === 'case-media' && page.media !== undefined ? (
        <CaseMediaFigure media={page.media} />
      ) : null}
    </>
  );
}

function SourcesList({ sources }: { sources: readonly LessonSource[] }) {
  return (
    <ol className={styles.sourceList}>
      {sources.map((source) => (
        <li key={source.id} className={styles.sourceItem}>
          <SourceCitation source={source} />
        </li>
      ))}
    </ol>
  );
}

function SourceCitation({ source }: { source: LessonSource }) {
  const outbound = sourceOutboundHref(source);
  const citation = `${source.authors}. ${String(source.year)}. ${source.title}. ${source.venue}.`;

  return (
    <>
      <p className={styles.sourceText}>{citation}</p>
      {outbound !== undefined ? (
        <p className={styles.sourceLink}>
          <a href={outbound} {...externalLinkProps(outbound)}>
            {source.doi !== undefined ? `DOI ${source.doi}` : source.title} (opens in a new tab)
          </a>
        </p>
      ) : null}
      {source.doi !== undefined && source.href !== undefined ? (
        <p className={styles.sourceLink}>
          <a href={source.href} {...externalLinkProps(source.href)}>
            Open copy (opens in a new tab)
          </a>
        </p>
      ) : null}
      {source.note !== undefined ? <p className={styles.sourceNote}>{source.note}</p> : null}
    </>
  );
}

function IsolationRoomFigure() {
  return (
    <figure className={styles.figure}>
      <img
        className={styles.figureImage}
        src="/media/path-room-screen.webp"
        alt="A silhouette facing a bright screen in a dark room. The face is not visible."
      />
      <figcaption className={styles.figureCaption}>
        Isolation can look like an ordinary night at a screen.
      </figcaption>
    </figure>
  );
}

function CaseMediaFigure({ media }: { media: LessonMedia }) {
  return (
    <figure className={styles.figure}>
      <img className={styles.figureImage} src={media.src} alt={media.alt} />
      <figcaption className={styles.figureCaption}>{media.caption}</figcaption>
    </figure>
  );
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

function isInsideActivity(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.closest('[data-lesson-activity]') !== null;
}
