import { useCallback, useEffect, useRef, useState } from 'react';

import styles from './FeedThreadFigure.module.css';

/** Everyday othering, classified as likely hate. No slur, no named person. */
export const FOCAL_COMMENT = "They don't belong here. There are other places they can go.";

const AGREEMENTS = [
  { id: 'agree_this', handle: '@handle_a', text: 'This.' },
  { id: 'agree_facts', handle: '@handle_b', text: 'Facts.' },
  { id: 'agree_louder', handle: '@handle_c', text: 'Say it louder.' },
] as const;

const FOLLOW_ON = [
  { id: 'more_market', handle: '@handle_4', text: 'Weekend market was packed.' },
  {
    id: 'more_recipe',
    handle: '@handle_5',
    text: 'Anyone still have that soup recipe from last night?',
  },
  { id: 'more_match', handle: '@handle_6', text: 'The match starts at eight. Do not be late.' },
  { id: 'more_traffic', handle: '@handle_7', text: 'The ring road is a joke today.' },
] as const;

/**
 * A generic thread that demonstrates a disposable feed, not a named platform.
 *
 * The focal comment is shown in full, in a dismissive register that can still
 * be classified as likely anti-Muslim hate. Agreeing replies arrive under it.
 * See more posts then buries the thread under unrelated chatter. The motion
 * is never the only path.
 */
export function FeedThreadFigure() {
  const [showMore, setShowMore] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  const handleSeeMore = useCallback((): void => {
    setShowMore(true);
  }, []);

  useEffect(() => {
    if (!showMore) {
      return;
    }

    const thread = threadRef.current;
    if (thread === null) {
      return;
    }

    if (typeof thread.scrollTo !== 'function') {
      return;
    }

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    thread.scrollTo({
      top: thread.scrollHeight,
      behavior: reduceMotion ? 'auto' : 'smooth',
    });
  }, [showMore]);

  return (
    <figure className={styles.figure}>
      <figcaption className={styles.caption}>
        <p className={styles.kicker}>A disposable thread</p>
        <p className={styles.title}>The remark arrives. The feed moves on.</p>
      </figcaption>

      <p className={styles.summary}>
        A generic news clip collects a remark classified as likely anti-Muslim hate. Agreeing
        replies pile on, then the feed replaces the thread with unrelated chatter. The wording is
        everyday othering, and this is not a named platform.
      </p>

      <div className={styles.platform} aria-hidden={false}>
        <header className={styles.chrome}>
          <span className={styles.dot} aria-hidden="true" />
          <span className={styles.dot} aria-hidden="true" />
          <span className={styles.dot} aria-hidden="true" />
          <p className={styles.chromeLabel}>Watch · Night desk</p>
        </header>

        <div ref={threadRef} className={styles.thread}>
          <article className={styles.post}>
            <p className={styles.postMeta}>Local news clip · 14 minutes ago</p>
            <p className={styles.postTitle}>A protest reaches the evening bulletin</p>
            <p className={styles.postBody}>
              The clip is public. The comments arrive faster than anyone can sit with the story.
            </p>
          </article>

          <article className={styles.focal}>
            <p className={styles.focalHandle}>@handle_0</p>
            <p className={styles.focalText}>{FOCAL_COMMENT}</p>
            <p className={styles.focalLabel}>Classified as likely anti-Muslim hate</p>
          </article>

          <ul className={styles.replies}>
            {AGREEMENTS.map((reply) => (
              <li key={reply.id} className={styles.replyItem}>
                <span className={styles.replyHandle}>{reply.handle}</span>
                <span className={styles.replyText}>{reply.text}</span>
              </li>
            ))}
          </ul>

          {showMore ? (
            <ul className={styles.more}>
              {FOLLOW_ON.map((post) => (
                <li key={post.id} className={styles.moreItem}>
                  <span className={styles.replyHandle}>{post.handle}</span>
                  <span className={styles.replyText}>{post.text}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      {showMore ? (
        <output className={styles.prompt}>See how quickly we move on?</output>
      ) : (
        <button type="button" className={styles.moreButton} onClick={handleSeeMore}>
          See more posts
        </button>
      )}
    </figure>
  );
}
