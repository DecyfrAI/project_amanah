import { useCallback, useState } from 'react';

import { ApiRequestError, type ExplorerItem } from '@/api';
import { PageSkeleton } from '@/components/ui/PageSkeleton';

import { useImagePosts } from './useImagePosts';

import styles from './ImageEvidenceList.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'Image posts could not be loaded. Try again.';
}

/**
 * Image posts that sit beside comment insights.
 *
 * Each card shows file metadata and a form note, not a slogan. The image stays
 * blurred until a person reveals it. Dataset annotations stay labeled as
 * annotations when the catalog is opened from Review.
 */
export function ImageEvidenceList() {
  const posts = useImagePosts();
  const [revealedId, setRevealedId] = useState<string | null>(null);
  const handleToggle = useCallback((id: string) => {
    setRevealedId((current) => (current === id ? null : id));
  }, []);

  return (
    <section className={styles.section} aria-labelledby="image-evidence-heading">
      <h2 id="image-evidence-heading" className={styles.heading}>
        Image evidence
      </h2>
      <p className={styles.lead}>
        Posts in this window that carry an image. Metadata is filename, size, and form. Comments
        stay in the insight cards above. The full research catalog, and a form to label a new image,
        live on Review.
      </p>
      {posts.isPending && <PageSkeleton label="image posts" />}
      {posts.isError && (
        <p className={styles.error} role="alert">
          {errorMessage(posts.error)}
        </p>
      )}
      {posts.isSuccess && posts.data.length === 0 && (
        <p className={styles.empty}>No image posts are in the reviewed example set.</p>
      )}
      {posts.isSuccess && posts.data.length > 0 && (
        <ul className={styles.list}>
          {posts.data.map((item) => (
            <li key={item.id}>
              <ImagePostCard
                item={item}
                revealed={revealedId === item.id}
                onToggle={handleToggle}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface ImagePostCardProps {
  readonly item: ExplorerItem;
  readonly revealed: boolean;
  readonly onToggle: (id: string) => void;
}

function ImagePostCard({ item, revealed, onToggle }: ImagePostCardProps) {
  const image = item.image;
  const handleClick = useCallback(() => {
    onToggle(item.id);
  }, [item.id, onToggle]);

  if (image === undefined || image === null) {
    return null;
  }

  return (
    <article className={styles.card} aria-labelledby={`${item.id}-title`}>
      <h3 id={`${item.id}-title`} className={styles.title}>
        {item.containerTitle}
      </h3>
      <p className={styles.meta}>
        {item.date} · item {item.id} · classified as{' '}
        {item.classification === 'likely_hate' ? 'likely anti-Muslim hate' : 'not hate'}
      </p>
      <p className={styles.note}>{image.formNote}</p>
      <dl className={styles.facts}>
        <div>
          <dt>File</dt>
          <dd>{image.filename}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{image.byteSize.toLocaleString('en')} bytes</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{image.mime}</dd>
        </div>
      </dl>
      <button
        type="button"
        className={styles.reveal}
        aria-expanded={revealed}
        aria-controls={`${item.id}-image`}
        onClick={handleClick}
      >
        {revealed ? 'Hide image' : 'Reveal image'}
      </button>
      <img
        id={`${item.id}-image`}
        className={revealed ? styles.image : `${styles.image} ${styles.imageBlurred}`}
        src={image.imageSrc}
        alt={image.altText}
      />
    </article>
  );
}
