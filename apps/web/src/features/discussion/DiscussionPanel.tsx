import { useCallback } from 'react';

import { ApiRequestError } from '@/api';
import type { DiscussionPost as DiscussionPostModel, ReactionKind } from '@/api/contracts';

import { Composer } from './Composer';
import { DiscussionPost } from './DiscussionPost';
import { useDiscussion } from './useDiscussion';

import styles from './DiscussionPanel.module.css';

interface DiscussionPanelProps {
  insightId: string;
}

interface DiscussionPostRowProps {
  post: DiscussionPostModel;
  onReact: (postId: string, kind: ReactionKind) => void;
  onRetract: (postId: string) => void;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The discussion could not be loaded. Try again.';
}

function DiscussionPostRow({ post, onReact, onRetract }: DiscussionPostRowProps) {
  const handleReact = useCallback(
    (kind: ReactionKind): void => {
      onReact(post.id, kind);
    },
    [onReact, post.id],
  );

  const handleRetract = useCallback((): void => {
    onRetract(post.id);
  }, [onRetract, post.id]);

  return (
    <li>
      <DiscussionPost post={post} onReact={handleReact} onRetract={handleRetract} />
    </li>
  );
}

export function DiscussionPanel({ insightId }: DiscussionPanelProps) {
  const { discussionQuery, createPost, react, retract } = useDiscussion(insightId);

  const handleRetry = useCallback((): void => {
    void discussionQuery.refetch();
  }, [discussionQuery]);

  const handleReact = useCallback(
    (postId: string, kind: ReactionKind): void => {
      react.mutate({ postId, kind });
    },
    [react],
  );

  const handleRetract = useCallback(
    (postId: string): void => {
      retract.mutate(postId);
    },
    [retract],
  );

  const handleCompose = useCallback(
    (body: string, attachFigure: boolean): void => {
      const input = attachFigure ? { body, captureId: 'cap_daily_rate' } : { body };
      createPost.mutate(input);
    },
    [createPost],
  );

  if (discussionQuery.isPending) {
    return <p className={styles.status}>Loading discussion</p>;
  }

  if (discussionQuery.isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(discussionQuery.error)}</p>
        <button type="button" className={styles.retry} onClick={handleRetry}>
          Try again
        </button>
      </div>
    );
  }

  const discussion = discussionQuery.data;

  return (
    <section className={styles.panel} aria-labelledby="discussion-heading">
      <h2 id="discussion-heading" className={styles.heading}>
        Discussion
      </h2>
      <p className={styles.lede}>
        Notes stay attached to this insight. React with Useful or Needs context. There is no ranking
        of people.
      </p>
      <ul className={styles.list}>
        {discussion.posts.map((post) => (
          <DiscussionPostRow
            key={post.id}
            post={post}
            onReact={handleReact}
            onRetract={handleRetract}
          />
        ))}
      </ul>
      {createPost.isError ? (
        <p className={styles.error} role="alert">
          {errorMessage(createPost.error)}
        </p>
      ) : null}
      <Composer isSubmitting={createPost.isPending} onSubmit={handleCompose} />
    </section>
  );
}
