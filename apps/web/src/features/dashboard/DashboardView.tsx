import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  ApiRequestError,
  type CreateInsightInput,
  type OverviewBreakdown,
  type OverviewDay,
  type OverviewMetric,
} from '@/api';
import { BreakdownChart } from '@/components/charts/BreakdownChart';
import { DailyRateChart } from '@/components/charts/DailyRateChart';
import { VolumeChart } from '@/components/charts/VolumeChart';
import { CoverageStrip } from '@/components/dashboard/CoverageStrip';
import { KpiCard } from '@/components/dashboard/KpiCard';
import { FilterBar } from '@/components/filters/FilterBar';
import { InfoTip } from '@/components/ui/InfoTip';
import { PageSkeleton } from '@/components/ui/PageSkeleton';
import { useCreateInsight } from '@/features/insights/useCreateInsight';

import { dayExplorerHref, metricExplorerHref } from './explorer-href';
import { findingFromBreakdownRow, findingFromDay, findingFromMetric } from './findings';
import { NewsStream } from './NewsStream';
import { FILTER_PARAMS, useDashboardFilters } from './useDashboardFilters';
import { useFilterOptions, useOverview } from './useOverview';

import styles from './DashboardView.module.css';

interface DashboardViewProps {
  heading: string;
  lead: string;
  /**
   * Where a day's supporting records live, or `null` where they are not
   * reachable from this chrome. Records sit behind authentication, so the public
   * dashboard passes `null` rather than offering a link into a login redirect.
   */
  explorerPath: string | null;
}

const VIEWS = [
  { id: 'rate', label: 'Rate over time' },
  { id: 'volume', label: 'Volume over time' },
] as const;

type ViewId = (typeof VIEWS)[number]['id'];

/** Which filter parameter a breakdown dimension hands to the Explorer. */
const DIMENSION_PARAM: Record<OverviewBreakdown['dimension'], string> = {
  hate_type: FILTER_PARAMS.hateType,
  platform: FILTER_PARAMS.platform,
  severity: FILTER_PARAMS.severity,
  review_state: FILTER_PARAMS.reviewState,
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The dashboard could not be loaded. Try again.';
}

/**
 * The dashboard itself: scope, key figures, a time series, and compositions.
 *
 * The caller supplies the heading and the drill-down path; everything numeric
 * comes from the same hook and the same contract, so a figure cannot differ
 * between two callers. Reading this requires a session: ADR 0001 and spec.md
 * FR-HOME-005 put every application surface behind authentication.
 */
export function DashboardView({ heading, lead, explorerPath }: DashboardViewProps) {
  const overviewQuery = useOverview();
  const optionsQuery = useFilterOptions();
  const { setRange, toggleValue, clearAll, activeCount, toSearch } = useDashboardFilters();
  const createInsight = useCreateInsight();
  const [view, setView] = useState<ViewId>('rate');

  const handleRetry = useCallback((): void => {
    void overviewQuery.refetch();
  }, [overviewQuery]);

  const canReport = explorerPath !== null;

  /**
   * A second click while the create is in flight is dropped (PA-04): the first
   * request will navigate to the stored insight, and repeating it would write a
   * duplicate record rather than re-open the same one.
   */
  const startInsight = useCallback(
    (finding: Parameters<typeof createInsight.mutate>[0]): void => {
      if (createInsight.isPending) {
        return;
      }
      createInsight.mutate(finding);
    },
    [createInsight],
  );

  const handleReportDay = useCallback(
    (day: OverviewDay): void => {
      const overview = overviewQuery.data;
      if (overview === undefined || explorerPath === null) {
        return;
      }
      const finding = findingFromDay(
        day,
        dayExplorerHref(explorerPath, toSearch(), day.date),
        overview.coverage.sources,
      );
      if (finding !== null) {
        startInsight(finding);
      }
    },
    [explorerPath, overviewQuery.data, startInsight, toSearch],
  );

  const buildBreakdownHref = useCallback(
    (dimension: OverviewBreakdown['dimension'], key: string): string => {
      const search = new URLSearchParams(toSearch());
      search.set(DIMENSION_PARAM[dimension], key);
      return `${explorerPath ?? ''}?${search.toString()}`;
    },
    [explorerPath, toSearch],
  );

  if (overviewQuery.isPending) {
    return <PageSkeleton label="the dashboard" />;
  }

  if (overviewQuery.isError) {
    return (
      <div className={styles.error} role="alert">
        <p>{errorMessage(overviewQuery.error)}</p>
        <button type="button" className={styles.retry} onClick={handleRetry}>
          Try again
        </button>
      </div>
    );
  }

  const overview = overviewQuery.data;
  const explorerHref = explorerPath === null ? null : `${explorerPath}${toSearch()}`;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{heading}</h1>
        <p className={styles.lead}>{lead}</p>
      </header>

      {optionsQuery.data !== undefined && (
        <FilterBar
          options={optionsQuery.data}
          applied={overview.applied}
          onRangeChange={setRange}
          onToggle={toggleValue}
          onClear={clearAll}
          activeCount={activeCount}
        />
      )}

      <CoverageStrip window={overview.window} coverage={overview.coverage} />

      <NewsStream />

      {overview.metrics.length === 0 ? (
        <p className={styles.empty}>
          No figures are available for this window. That usually means collection has not run for
          the selected dates rather than that nothing was found.
        </p>
      ) : (
        <section aria-labelledby="kpi-heading">
          <div className={styles.headingRow}>
            <h2 id="kpi-heading" className={styles.sectionHeading}>
              Key figures
            </h2>
            <InfoTip label="Key figures">
              Each card is a rate or a count for this window. The value never appears without its
              numerator and denominator, and a model-only figure says so in words.
            </InfoTip>
          </div>
          <div className={styles.kpis}>
            {overview.metrics.map((metric) => (
              <ReportableKpi
                key={metric.id}
                metric={metric}
                from={overview.window.from}
                to={overview.window.to}
                sources={overview.coverage.sources}
                itemsObserved={overview.coverage.itemsObserved}
                itemsRelevant={overview.coverage.itemsRelevant}
                explorerBase={explorerHref}
                canReport={canReport}
                onCreate={startInsight}
              />
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="trend-heading">
        <div className={styles.sectionHead}>
          <div className={styles.headingRow}>
            <h2 id="trend-heading" className={styles.sectionHeading}>
              Over time
            </h2>
            <InfoTip label="Over time">
              Rate is likely hate as a share of Muslim-related items. Volume is the same days
              stacked by source. A gap day has no line and no bar.
            </InfoTip>
          </div>
          <fieldset className={styles.viewToggle}>
            <legend className="visually-hidden">Choose how the series is drawn</legend>
            {VIEWS.map((entry) => (
              <ViewButton
                key={entry.id}
                id={entry.id}
                label={entry.label}
                isActive={view === entry.id}
                onSelect={setView}
              />
            ))}
          </fieldset>
        </div>

        {view === 'rate' ? (
          <div className={styles.seriesStack}>
            <DailyRateChart
              days={overview.daily}
              explorerPath={explorerPath}
              explorerSearch={toSearch()}
              {...(canReport ? { onReportDay: handleReportDay } : {})}
            />
            <VolumeChart
              days={overview.daily}
              explorerPath={explorerPath}
              explorerSearch={toSearch()}
            />
          </div>
        ) : (
          <VolumeChart
            days={overview.daily}
            explorerPath={explorerPath}
            explorerSearch={toSearch()}
          />
        )}
      </section>

      <section aria-labelledby="composition-heading">
        <div className={styles.sectionHead}>
          <div className={styles.headingRow}>
            <h2 id="composition-heading" className={styles.sectionHeading}>
              What the likely-hate items are made of
            </h2>
            <InfoTip label="Composition">
              Shares among items already classified as likely anti-Muslim hate. Each row can open
              the Explorer on that slice when a session can reach the records.
            </InfoTip>
          </div>
          {explorerHref !== null && (
            <Link className={styles.sectionLink} to={explorerHref}>
              Open these items in the Explorer
            </Link>
          )}
        </div>

        <div className={styles.breakdowns}>
          {overview.breakdowns.map((breakdown) => (
            <ReportableBreakdown
              key={breakdown.id}
              breakdown={breakdown}
              buildHref={explorerPath === null ? null : buildBreakdownHref}
              from={overview.window.from}
              to={overview.window.to}
              sources={overview.coverage.sources}
              explorerBase={explorerHref}
              itemsObserved={overview.coverage.itemsObserved}
              itemsRelevant={overview.coverage.itemsRelevant}
              canReport={canReport}
              onCreate={startInsight}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

interface ReportableKpiProps {
  metric: OverviewMetric;
  from: string;
  to: string;
  sources: readonly string[];
  itemsObserved: number;
  itemsRelevant: number;
  explorerBase: string | null;
  canReport: boolean;
  onCreate: (input: CreateInsightInput) => void;
}

function ReportableKpi({
  metric,
  from,
  to,
  sources,
  itemsObserved,
  itemsRelevant,
  explorerBase,
  canReport,
  onCreate,
}: ReportableKpiProps) {
  const handleReport = useCallback((): void => {
    const finding = findingFromMetric(
      metric,
      from,
      to,
      explorerBase ?? '/app/explorer',
      sources,
      itemsObserved,
      itemsRelevant,
    );
    if (finding !== null) {
      onCreate(finding);
    }
  }, [explorerBase, from, itemsObserved, itemsRelevant, metric, onCreate, sources, to]);

  return (
    <KpiCard
      metric={metric}
      explorerHref={explorerBase === null ? null : metricExplorerHref(explorerBase, '', metric.id)}
      {...(canReport &&
      findingFromMetric(
        metric,
        from,
        to,
        explorerBase ?? '/app/explorer',
        sources,
        itemsObserved,
        itemsRelevant,
      ) !== null
        ? { onReport: handleReport }
        : {})}
    />
  );
}

interface ReportableBreakdownProps {
  breakdown: OverviewBreakdown;
  buildHref: ((dimension: OverviewBreakdown['dimension'], key: string) => string) | null;
  from: string;
  to: string;
  sources: readonly string[];
  explorerBase: string | null;
  itemsObserved: number;
  itemsRelevant: number;
  canReport: boolean;
  onCreate: (input: CreateInsightInput) => void;
}

function ReportableBreakdown({
  breakdown,
  buildHref,
  from,
  to,
  sources,
  explorerBase,
  itemsObserved,
  itemsRelevant,
  canReport,
  onCreate,
}: ReportableBreakdownProps) {
  const handleReport = useCallback(
    (key: string): void => {
      const href = explorerBase ?? '/app/explorer';
      const finding = findingFromBreakdownRow(
        breakdown,
        key,
        from,
        to,
        href,
        sources,
        itemsObserved,
        itemsRelevant,
      );
      if (finding !== null) {
        onCreate(finding);
      }
    },
    [breakdown, explorerBase, from, itemsObserved, itemsRelevant, onCreate, sources, to],
  );

  return (
    <BreakdownChart
      breakdown={breakdown}
      buildHref={buildHref}
      {...(canReport ? { onReportRow: handleReport } : {})}
    />
  );
}

interface ViewButtonProps {
  id: ViewId;
  label: string;
  isActive: boolean;
  onSelect: (id: ViewId) => void;
}

function ViewButton({ id, label, isActive, onSelect }: ViewButtonProps) {
  const handleClick = useCallback((): void => {
    onSelect(id);
  }, [id, onSelect]);

  return (
    <button
      type="button"
      className={isActive ? `${styles.viewButton} ${styles.viewButtonOn}` : styles.viewButton}
      onClick={handleClick}
      aria-pressed={isActive}
    >
      {label}
    </button>
  );
}
