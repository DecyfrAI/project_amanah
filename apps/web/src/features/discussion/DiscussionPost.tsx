import { FIXTURE_VIEWER } from '@/api';
import type { DiscussionPost as DiscussionPostModel, ReactionKind } from '@/api/contracts';

import { CaptureFigure } from './CaptureFigure';
import { ReactionBar } from './ReactionBar';

import styles from './DiscussionPost.module.css';

interface DiscussionPostProps {
  post: DiscussionPostModel;
  onReact: (kind: ReactionKind) => void;
  onRetract: () => void;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  }).format(date);
}

export function DiscussionPost({ post, onReact, onRetract }: DiscussionPostProps) {
  const isRetracted = post.retractedAt !== null;
  const canRetract = post.author.id === FIXTURE_VIEWER.id && !isRetracted;

  return (
    <article className={styles.post} aria-labelledby={`post-${post.id}-author`}>
      <header className={styles.meta}>
        <h3 id={`post-${post.id}-author`} className={styles.author}>
          {post.author.displayName}
        </h3>
        <p className={styles.time}>
          <time dateTime={post.createdAt}>{formatTimestamp(post.createdAt)}</time>
        </p>
      </header>
      <p className={styles.body}>{post.body}</p>
      {post.capture !== null && !isRetracted ? <CaptureFigure capture={post.capture} /> : null}
      {isRetracted ? null : (
        <ReactionBar reactions={post.reactions} disabled={false} onReact={onReact} />
      )}
      {canRetract ? (
        <button type="button" className={styles.retract} onClick={onRetract}>
          Retract this note
        </button>
      ) : null}
    </article>
  );
}
