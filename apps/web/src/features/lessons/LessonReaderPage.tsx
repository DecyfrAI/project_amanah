import { Link, useParams } from 'react-router-dom';

import { usePageTitle } from '@/hooks/usePageTitle';

import { LessonReader } from './LessonReader';
import { getLessonContent, lessonCatalogPath } from './lesson-copy';

import styles from './LessonReader.module.css';

interface LessonReaderPageProps {
  /** Extra page padding when the marketing header is fixed above this view. */
  framedForMarketing?: boolean;
}

/**
 * Route wrapper for one syllabus module. Invalid ids stay on an actionable
 * error. Content is local, so there is no fetch state to render.
 */
export function LessonReaderPage({ framedForMarketing = false }: LessonReaderPageProps) {
  const { lessonId } = useParams<{ lessonId: string }>();
  const module = lessonId === undefined ? undefined : getLessonContent(lessonId);
  const catalogTo = lessonCatalogPath(framedForMarketing);
  const shellClass = framedForMarketing ? `${styles.shell} ${styles.shellPublic}` : styles.shell;

  usePageTitle(module === undefined ? 'Lesson' : `${module.number} ${module.title}`);

  if (module === undefined) {
    return (
      <div className={shellClass}>
        <div className={styles.error} role="alert">
          <p>This page is not in Lessons.</p>
          <p>Open the catalog and pick a numbered module or a case study.</p>
          <p>
            <Link to={catalogTo}>Back to Lessons</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={shellClass}>
      <LessonReader key={module.id} module={module} catalogTo={catalogTo} />
    </div>
  );
}
