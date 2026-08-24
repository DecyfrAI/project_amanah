import { useCallback } from 'react';

import { ApiRequestError, type NewsItem } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';

import {
  articleLinkLabel,
  formatNewsPublishedAt,
  NEWS_HEADING,
  NEWS_LEAD,
  outboundCue,
} from './news-copy';
import { useNews } from './useNews';

import styles from './NewsStream.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The news stream could not be loaded. Try again.';
}

/**
 * Context headlines that coincide with the Overview window.
 *
 * Specification v2 §6.1 and §7.1 put current news on the public dashboard for
 * P0. This is not the F-S7/F-S8 classified news-item card: there is no model
 * label here. Language stays temporal ("coincides with"), never causal.
 */
export function NewsStream() {
  const newsQuery = useNews();

  const handleRetry = useCallback((): void => {
    void newsQuery.refetch();
  }, [newsQuery]);

  return (
    <section className={styles.section} aria-labelledby="news-heading">
      <div className={styles.headingRow}>
        <h2 id="news-heading" className={styles.heading}>
          {NEWS_HEADING}
        </h2>
        <InfoTip label={NEWS_HEADING}>
          Published news that coincides with this date window. These are not Amanah classifications.
          An article here is context, not a finding of hate.
        </InfoTip>
      </div>
      <p className={styles.lead}>{NEWS_LEAD}</p>
      <NewsBody
        isPending={newsQuery.isPending}
        isError={newsQuery.isError}
        error={newsQuery.error}
        items={newsQuery.data?.items}
        onRetry={handleRetry}
      />
    </section>
  );
}

interface NewsBodyProps {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  items: readonly NewsItem[] | undefined;
  onRetry: () => void;
}

function NewsBody({ isPending, isError, error, items, onRetry }: NewsBodyProps) {
  if (isPending) {
    return (
      <output className={styles.status} aria-live="polite" aria-busy="true">
        <span className="visually-hidden">Loading the news stream</span>
        <div className={styles.skeleton} aria-hidden="true">
          <div className={`${styles.bar} ${styles.barWide}`} />
          <div className={`${styles.bar} ${styles.barMedium}`} />
        </div>
      </output>
    );
  }

  if (isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(error)}</p>
        <button type="button" className={styles.retry} onClick={onRetry}>
          Try again
        </button>
      </div>
    );
  }

  if (items === undefined || items.length === 0) {
    return (
      <p className={styles.empty}>
        No published articles sit in this window. That is a gap in ingested news, not a claim that
        nothing happened.
      </p>
    );
  }

  return (
    <ul className={styles.list}>
      {items.map((item) => (
        <li key={item.id}>
          <NewsArticle item={item} />
        </li>
      ))}
    </ul>
  );
}

interface NewsArticleProps {
  item: NewsItem;
}

function NewsArticle({ item }: NewsArticleProps) {
  const published = formatNewsPublishedAt(item.published_at);
  const headingId = `${item.id}-headline`;

  return (
    <article className={styles.item} aria-labelledby={headingId}>
      <p className={styles.meta}>
        <span className={styles.outlet}>{item.source_name}</span>
        {item.published_at === null ? (
          <span>{published.absolute}</span>
        ) : (
          <time dateTime={item.published_at}>
            {published.absolute} ({published.relative})
          </time>
        )}
      </p>
      <h3 id={headingId} className={styles.headline}>
        <a
          className={styles.headlineLink}
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={articleLinkLabel(item.title, item.source_name)}
        >
          {item.title}
        </a>
      </h3>
      <p className={styles.outbound}>{outboundCue(item.source_name)}</p>
      <p className={styles.summary}>{item.summary}</p>
    </article>
  );
}
