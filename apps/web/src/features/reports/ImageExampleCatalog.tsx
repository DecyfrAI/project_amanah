import { ApiRequestError, hateTypeLabel, type ImageExample } from '@/api';
import { SafeImage } from '@/components/ui/SafeImage';

import { useImageExamples } from './useImageExamples';

import styles from './ImageExampleCatalog.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The example catalog could not be loaded. Refresh the page and try again.';
}

/**
 * Research corpus of sourced memes. Images follow the viewer's own display
 * preference (PA-01) and keep a per-image Show/Hide control. Dataset
 * annotations stay labeled as annotations, never as Amanah findings.
 */
export function ImageExampleCatalog() {
  const catalog = useImageExamples();

  return (
    <section className={styles.card} aria-labelledby="image-examples-heading">
      <h2 className={styles.heading} id="image-examples-heading">
        Research image examples
      </h2>
      <p className={styles.lead}>
        Sourced public memes used as a research corpus. Each row keeps a dataset annotation separate
        from the prediction. Images follow your display preference in Settings, and each one has its
        own Show and Hide control. They are not for redistribution.
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
              <ExampleCard item={item} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface ExampleCardProps {
  readonly item: ImageExample;
}

function ExampleCard({ item }: ExampleCardProps) {
  const annotation = item.dataset_annotation;
  const types = annotation.hate_types.map(hateTypeLabel).join(', ');
  const severity =
    annotation.severity === null
      ? 'no severity recorded'
      : `severity ${String(annotation.severity)}`;

  return (
    <article className={styles.example} aria-labelledby={`${item.id}-title`}>
      <h3 className={styles.title} id={`${item.id}-title`}>
        {item.title}
      </h3>
      <p className={styles.meta}>
        {types === '' ? 'No dataset hate type' : types} · {severity}
      </p>
      <p className={styles.note}>{item.form_note}</p>
      <SafeImage src={item.image_src} alt={item.alt_text} subject="example" />
    </article>
  );
}
