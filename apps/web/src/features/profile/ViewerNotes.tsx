import { Link } from 'react-router-dom';

import { ApiRequestError, type ViewerPost } from '@/api';
import { PageSkeleton } from '@/components/ui/PageSkeleton';

import { useViewerPosts } from './useViewerPosts';

import styles from './ViewerNotes.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'Your notes could not be loaded. Try again.';
}

function formatPostedAt(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/**
 * The viewer's own discussion notes, listed on the profile.
 *
 * This is not a forum feed. Each row is a note the signed-in person left on an
 * insight, so they can return to that thread. Other people's notes never appear
 * here, and there is no ranking of authors.
 */
export function ViewerNotes() {
  const notesQuery = useViewerPosts();

  if (notesQuery.isPending) {
    return <PageSkeleton label="your notes" />;
  }

  if (notesQuery.isError) {
    return (
      <p className={styles.error} role="alert">
        {errorMessage(notesQuery.error)}
      </p>
    );
  }

  const posts = notesQuery.data.posts;

  return (
    <section className={styles.panel} aria-labelledby="notes-heading">
      <h2 id="notes-heading" className={styles.heading}>
        Your notes
      </h2>
      <p className={styles.lede}>
        Notes you have left on insights. Each one stays attached to its finding. This is not a
        public forum, and it does not rank anyone.
      </p>

      {posts.length === 0 ? (
        <p className={styles.empty}>
          You have not left a note yet. Open an insight and add one there if you want to come back
          to it from here.
        </p>
      ) : (
        <ul className={styles.list}>
          {posts.map((post) => (
            <NoteRow key={post.id} post={post} />
          ))}
        </ul>
      )}
    </section>
  );
}

interface NoteRowProps {
  post: ViewerPost;
}

function NoteRow({ post }: NoteRowProps) {
  const isRetracted = post.retractedAt !== null;

  return (
    <li className={styles.item}>
      <p className={styles.meta}>
        On{' '}
        <Link className={styles.insightLink} to={`/app/insights/${post.insightId}`}>
          {post.insightTitle}
        </Link>
        <span className={styles.when}> · {formatPostedAt(post.createdAt)}</span>
      </p>
      <p className={isRetracted ? styles.retracted : styles.body}>{post.body}</p>
    </li>
  );
}
