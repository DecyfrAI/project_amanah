import { ApiRequestError } from '@/api';
import { FilterBar } from '@/components/filters/FilterBar';
import { PageSkeleton } from '@/components/ui/PageSkeleton';
import { useDashboardFilters } from '@/features/dashboard/useDashboardFilters';
import { useFilterOptions } from '@/features/dashboard/useOverview';
import { usePageTitle } from '@/hooks/usePageTitle';

import { ExplorerSearch } from './ExplorerSearch';
import { ItemsTable } from './ItemsTable';
import { useItems } from './useItems';

import styles from './ExplorerPage.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'Those records could not be loaded. Try again.';
}

/**
 * Item-level records behind the figures.
 *
 * This is where a drill-down from the dashboard lands, carrying the same filters,
 * so the reader can check a number against the material it came from. The rows
 * sit in a scrollable table: filters stay in the bar and the URL, and each
 * excerpt is synthetic wording shown in full.
 *
 * The fixture holds a small reviewed set rather than the thousands the aggregates
 * describe. The page says so rather than letting the count imply otherwise.
 */
export function ExplorerPage() {
  usePageTitle('Explorer');

  const itemsQuery = useItems();
  const optionsQuery = useFilterOptions();
  const { filters, setRange, setQuery, toggleValue, clearAll, activeCount } = useDashboardFilters();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Explorer</h1>
        <p className={styles.lead}>
          The records behind the figures, as a table you can filter and search. Comment rows show
          synthetic wording in full. Image rows show form, filename, and size. There is no author
          view here, and there will not be one.
        </p>
      </header>

      {itemsQuery.data !== undefined && (
        <ExplorerSearch
          key={filters.q ?? ''}
          value={filters.q ?? ''}
          items={itemsQuery.data.items}
          onQueryChange={setQuery}
        />
      )}

      {optionsQuery.data !== undefined && itemsQuery.data !== undefined && (
        <FilterBar
          options={optionsQuery.data}
          applied={itemsQuery.data.applied}
          onRangeChange={setRange}
          onToggle={toggleValue}
          onClear={clearAll}
          activeCount={activeCount}
        />
      )}

      {itemsQuery.isPending && <PageSkeleton label="these records" />}

      {itemsQuery.isError && (
        <p className={styles.error} role="alert">
          {errorMessage(itemsQuery.error)}
        </p>
      )}

      {itemsQuery.data !== undefined && (
        <>
          <p className={styles.count} aria-live="polite">
            {itemsQuery.data.matched === 0
              ? 'No reviewed examples match these filters.'
              : `Showing ${String(itemsQuery.data.returned)} of ${String(itemsQuery.data.matched)} reviewed examples for ${itemsQuery.data.applied.from} to ${itemsQuery.data.applied.to}.`}
          </p>

          <p className={styles.caveat}>
            These are hand-reviewed examples held in the demo fixture, not the full collection. The
            counts on the dashboard come from the aggregate record, so this list is deliberately
            much shorter and must not be read as the whole of what was collected.
          </p>

          {itemsQuery.data.matched === 0 ? (
            <p className={styles.empty}>
              Nothing here matches. Widen the window or clear a filter. An empty result means no
              example matched these filters, not that the days were quiet.
            </p>
          ) : (
            <ItemsTable items={itemsQuery.data.items} />
          )}
        </>
      )}
    </div>
  );
}
