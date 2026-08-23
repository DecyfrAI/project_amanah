import { useCallback, useState } from 'react';

import { ApiRequestError, hateTypeLabel, type ImageExample } from '@/api';

import { useImageExamples } from './useImageExamples';

import styles from './ImageExampleCatalog.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The example catalog could not be loaded. Refresh the page and try again.';
}

/**
 * Research corpus of sourced memes. Harmful media stays blurred until a
 * person reveals it. Dataset annotations stay labeled as annotations.
 */
export function ImageExampleCatalog() {
  const catalog = useImageExamples();
  const [revealedId, setRevealedId] = useState<string | null>(null);
  const handleToggle = useCallback((id: string) => {
    setRevealedId((current) => (current === id ? null : id));
  }, []);

  return (
    <section className={styles.card} aria-labelledby="image-examples-heading">
      <h2 className={styles.heading} id="image-examples-heading">
        Research image examples
      </h2>
      <p className={styles.lead}>
        Sourced public memes used as a research corpus. Each row keeps a dataset annotation separate
        from the fixture prediction. Images stay blurred until you reveal them. A later importer can
        seed these files into object storage and Postgres. They are not for redistribution.
      </p>
      {catalog.isPending && <p className={styles.lead}>Loading the example catalog.</p>}
      {catalog.isError && (
        <p className={styles.error} role="alert">
          {errorMessage(catalog.error)}
        </p>
      )}
      {catalog.isSuccess && (
        <ul className={styles.grid}>
          {catalog.data.items.map((item) => (
            <li key={item.id}>
              <ExampleCard item={item} revealed={revealedId === item.id} onToggle={handleToggle} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface ExampleCardProps {
  readonly item: ImageExample;
  readonly revealed: boolean;
  readonly onToggle: (id: string) => void;
}

function ExampleCard({ item, revealed, onToggle }: ExampleCardProps) {
  const handleClick = useCallback(() => {
    onToggle(item.id);
  }, [item.id, onToggle]);

  return (
    <article className={styles.example} aria-labelledby={`${item.id}-title`}>
      <h3 className={styles.title} id={`${item.id}-title`}>
        {item.title}
      </h3>
      <p className={styles.meta}>
        {item.dataset_annotation.hate_types.map(hateTypeLabel).join(', ')} · severity{' '}
        {item.dataset_annotation.severity}
      </p>
      <p className={styles.note}>{item.form_note}</p>
      <button
        type="button"
        className={styles.reveal}
        aria-expanded={revealed}
        aria-controls={`${item.id}-image`}
        onClick={handleClick}
      >
        {revealed ? 'Hide example' : 'Reveal example'}
      </button>
      <img
        id={`${item.id}-image`}
        className={revealed ? styles.image : `${styles.image} ${styles.imageBlurred}`}
        src={item.image_src}
        alt={item.alt_text}
      />
    </article>
  );
}
