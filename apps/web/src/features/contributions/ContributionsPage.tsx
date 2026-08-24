import { useCallback } from 'react';
import { Link } from 'react-router-dom';

import { ApiRequestError, type WireContributionSummary } from '@/api';
import { StatusPill, type StatusIndicator } from '@/components/ui/StatusPill';
import { usePageTitle } from '@/hooks/usePageTitle';

import { useContributions } from './useContributions';

import styles from './ContributionsPage.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'Your contributions could not be loaded. Try again.';
}

const TYPE_LABELS: Record<string, string> = {
  url_submission: 'URL submission',
  classification_dispute: 'Classification dispute',
  prepared_platform_report: 'Prepared platform report',
};

/**
 * How a status reads as a visual state.
 *
 * `prepared` is deliberately *pending* rather than ok: the report exists but
 * nobody has filed it, and showing it as complete would imply Amanah did.
 */
const STATUS_INDICATORS: Record<string, StatusIndicator> = {
  prepared: 'pending',
  submitted: 'ok',
  closed: 'ok',
  processing: 'pending',
  analyzed: 'ok',
  duplicate: 'degraded',
  unsupported: 'degraded',
  inaccessible: 'degraded',
  rejected: 'degraded',
  failed: 'degraded',
  open: 'pending',
  upheld: 'ok',
  declined: 'degraded',
};

function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

/**
 * Your Contributions (spec §9.10, F-S11).
 *
 * One history across URL submissions, classification disputes, and prepared
 * platform reports. Owner-scoped on the server: a user reads only their own
 * records, and no row here carries evidence, an author identifier, or a
 * reviewer's private note.
 */
export function ContributionsPage() {
  usePageTitle('Your contributions');
  const contributionsQuery = useContributions();

  const handleRetry = useCallback((): void => {
    void contributionsQuery.refetch();
  }, [contributionsQuery]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Your contributions</h1>
        <p className={styles.lead}>
          Everything you submitted, disputed, or prepared, newest first. Only you can read these.
        </p>
      </header>

      <p className={styles.disclosure}>
        A prepared report is wording you saved for yourself. Amanah never submits a report to a
        platform, so &ldquo;submitted&rdquo; here means you told us you filed it.
      </p>

      <ContributionsBody
        isPending={contributionsQuery.isPending}
        isError={contributionsQuery.isError}
        error={contributionsQuery.error}
        items={contributionsQuery.data?.items}
        onRetry={handleRetry}
      />
    </div>
  );
}

interface ContributionsBodyProps {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  items: readonly WireContributionSummary[] | undefined;
  onRetry: () => void;
}

function ContributionsBody({ isPending, isError, error, items, onRetry }: ContributionsBodyProps) {
  if (isPending) {
    return (
      <output className={styles.status} aria-live="polite" aria-busy="true">
        Loading your contributions
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
        You have not contributed anything yet. Submitting a URL, disputing a classification, or
        preparing a platform report will show up here.
      </p>
    );
  }

  return (
    <ul className={styles.list}>
      {items.map((contribution) => (
        <li key={contribution.id}>
          <ContributionRow contribution={contribution} />
        </li>
      ))}
    </ul>
  );
}

function ContributionRow({ contribution }: { contribution: WireContributionSummary }) {
  const typeLabel = TYPE_LABELS[contribution.contribution_type] ?? contribution.contribution_type;

  return (
    <article className={styles.row} aria-labelledby={`${contribution.id}-title`}>
      <div className={styles.rowTop}>
        <h2 id={`${contribution.id}-title`} className={styles.rowTitle}>
          {typeLabel}
        </h2>
        <StatusPill
          indicator={STATUS_INDICATORS[contribution.status] ?? 'pending'}
          label={contribution.status.replaceAll('_', ' ')}
        />
      </div>

      <dl className={styles.facts}>
        <div className={styles.fact}>
          <dt className={styles.term}>Label</dt>
          <dd className={styles.value}>{contribution.label}</dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Created</dt>
          <dd className={styles.value}>{formatDate(contribution.created_at)}</dd>
        </div>
        <div className={styles.fact}>
          <dt className={styles.term}>Last update</dt>
          <dd className={styles.value}>
            {contribution.updated_at === null
              ? 'No change since'
              : formatDate(contribution.updated_at)}
          </dd>
        </div>
      </dl>

      {contribution.destination_item_id !== null && (
        <Link
          className={styles.link}
          to={`/app/explorer/${encodeURIComponent(contribution.destination_item_id)}`}
        >
          Open the item this refers to
        </Link>
      )}
    </article>
  );
}
