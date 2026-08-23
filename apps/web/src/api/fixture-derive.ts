import type {
  AppliedFilters,
  FilterOptions,
  Overview,
  OverviewBreakdown,
  OverviewDay,
  OverviewMetric,
} from './contracts';

/**
 * Shape of the generated collection fixture, scripts/build_fixture_collection.py.
 *
 * Declared here rather than validated with Zod because it is a build input rather
 * than a response: it never crosses a network boundary, and the schemas it feeds
 * are validated on the way out.
 */
export interface CollectionPlatformDay {
  readonly platform: string;
  readonly containers: number;
  readonly observed: number;
  readonly relevant: number;
  readonly nonRelevant: number;
  readonly likelyHate: number;
  readonly reviewConfirmed: number;
  readonly reviewCorrected: number;
  readonly reviewPending: number;
  readonly types: Readonly<Record<string, number>>;
  readonly severity: Readonly<Record<string, number>>;
}

export interface CollectionDay {
  readonly date: string;
  readonly collected: boolean;
  readonly platforms: readonly CollectionPlatformDay[];
}

export interface CollectionDocument {
  readonly available: { readonly from: string; readonly to: string; readonly timezone: string };
  readonly defaultWindowDays: number;
  readonly lastSuccessfulRun: string;
  readonly platforms: readonly {
    readonly platform: string;
    readonly containerLabel: string;
    readonly containers: number;
  }[];
  readonly hateTypes: readonly string[];
  readonly severityBands: readonly string[];
  readonly gapDays: readonly string[];
  readonly days: readonly CollectionDay[];
}

export interface OverviewFilters {
  from?: string | undefined;
  to?: string | undefined;
  platforms?: readonly string[] | undefined;
  hateTypes?: readonly string[] | undefined;
  severityBands?: readonly string[] | undefined;
  reviewStates?: readonly string[] | undefined;
  /** Keyword search for Explorer rows. Empty means no text filter. */
  q?: string | undefined;
}

export const REVIEW_STATES = ['pending', 'confirmed', 'corrected'] as const;

const HATE_TYPE_LABELS: Record<string, string> = {
  animosity: 'Animosity',
  derogation: 'Derogation',
  dehumanisation: 'Dehumanisation',
  dehumanization: 'Dehumanization',
  exclusion: 'Exclusion or segregation',
  threat: 'Threat or incitement',
  threat_or_incitement: 'Threat or incitement',
  collective_blame: 'Collective blame',
  other: 'Other',
};

const PLATFORM_LABELS: Record<string, string> = {
  youtube: 'YouTube',
  reddit: 'Reddit',
};

const SEVERITY_LABELS: Record<string, string> = {
  '0': 'Severity 0, borderline',
  '1': 'Severity 1, low',
  '2': 'Severity 2, moderate',
  '3': 'Severity 3, severe',
};

const REVIEW_LABELS: Record<string, string> = {
  pending: 'Awaiting review',
  confirmed: 'Confirmed by a reviewer',
  corrected: 'Corrected by a reviewer',
};

export function platformLabel(platform: string): string {
  return PLATFORM_LABELS[platform] ?? platform;
}

export function hateTypeLabel(type: string): string {
  return HATE_TYPE_LABELS[type] ?? type;
}

export function severityLabel(band: string): string {
  return SEVERITY_LABELS[band] ?? `Severity ${band}`;
}

export function reviewLabel(state: string): string {
  return REVIEW_LABELS[state] ?? state;
}

/**
 * A rate the interface is allowed to print, or null.
 *
 * Below this many relevant items a daily or sliced rate swings so far on one item
 * that stating it would imply precision the sample cannot carry.
 */
const MIN_DENOMINATOR = 8;

export function rateOf(numerator: number, denominator: number): number | null {
  if (denominator < MIN_DENOMINATOR) {
    return null;
  }
  return numerator / denominator;
}

function sumValues(counts: Readonly<Record<string, number>>, keys: readonly string[]): number {
  return keys.reduce((total, key) => total + (counts[key] ?? 0), 0);
}

/**
 * Likely-hate items on one platform-day that match the classification selection.
 *
 * Type, severity and review state are three views of the same set, so a selection
 * on more than one of them cannot be intersected from counts alone. The narrowest
 * matching count wins, which is the honest reading of what the fixture knows, and
 * the interface says which selection produced the figure.
 */
export function selectedHate(row: CollectionPlatformDay, filters: OverviewFilters): number {
  const candidates: number[] = [row.likelyHate];

  if (filters.hateTypes !== undefined && filters.hateTypes.length > 0) {
    candidates.push(sumValues(row.types, filters.hateTypes));
  }
  if (filters.severityBands !== undefined && filters.severityBands.length > 0) {
    candidates.push(sumValues(row.severity, filters.severityBands));
  }
  if (filters.reviewStates !== undefined && filters.reviewStates.length > 0) {
    const byState: Record<string, number> = {
      pending: row.reviewPending,
      confirmed: row.reviewConfirmed,
      corrected: row.reviewCorrected,
    };
    candidates.push(sumValues(byState, filters.reviewStates));
  }

  return Math.min(...candidates);
}

function isSelectedPlatform(platform: string, filters: OverviewFilters): boolean {
  return (
    filters.platforms === undefined ||
    filters.platforms.length === 0 ||
    filters.platforms.includes(platform)
  );
}

function clampDate(value: string | undefined, fallback: string, available: string[]): string {
  if (value === undefined || !available.includes(value)) {
    return fallback;
  }
  return value;
}

export function resolveWindow(
  document: CollectionDocument,
  filters: OverviewFilters,
): { from: string; to: string } {
  const dates = document.days.map((day) => day.date);
  const last = dates.at(-1) ?? document.available.to;
  const defaultFrom = dates.at(-document.defaultWindowDays) ?? dates[0] ?? document.available.from;

  const to = clampDate(filters.to, last, dates);
  const from = clampDate(filters.from, defaultFrom, dates);

  // A reversed range is a client mistake, not a reason to render nothing.
  return from <= to ? { from, to } : { from: to, to: from };
}

export function appliedFilters(
  document: CollectionDocument,
  filters: OverviewFilters,
): AppliedFilters {
  const window = resolveWindow(document, filters);
  return {
    from: window.from,
    to: window.to,
    platforms: [...(filters.platforms ?? [])],
    hateTypes: [...(filters.hateTypes ?? [])],
    severityBands: [...(filters.severityBands ?? [])],
    reviewStates: [...(filters.reviewStates ?? [])],
  };
}

function daysInWindow(
  document: CollectionDocument,
  window: { from: string; to: string },
): readonly CollectionDay[] {
  return document.days.filter((day) => day.date >= window.from && day.date <= window.to);
}

function dailySeries(days: readonly CollectionDay[], filters: OverviewFilters): OverviewDay[] {
  return days.map((day) => {
    if (!day.collected) {
      // Null, never zero. A failed collection is an absence of knowledge.
      return {
        date: day.date,
        collected: false,
        observed: null,
        relevant: null,
        likelyHate: null,
        nonRelevant: null,
        sources: [],
      };
    }

    const rows = day.platforms.filter((row) => isSelectedPlatform(row.platform, filters));
    const sources = rows
      .map((row) => ({
        key: row.platform,
        label: platformLabel(row.platform),
        likelyHate: selectedHate(row, filters),
        relevant: row.relevant,
      }))
      .toSorted((left, right) =>
        right.likelyHate === left.likelyHate
          ? right.relevant - left.relevant
          : right.likelyHate - left.likelyHate,
      );

    return {
      date: day.date,
      collected: true,
      observed: rows.reduce((total, row) => total + row.observed, 0),
      relevant: rows.reduce((total, row) => total + row.relevant, 0),
      nonRelevant: rows.reduce((total, row) => total + row.nonRelevant, 0),
      likelyHate: rows.reduce((total, row) => total + selectedHate(row, filters), 0),
      sources,
    };
  });
}

interface Totals {
  observed: number;
  relevant: number;
  likelyHate: number;
  selectedHate: number;
  confirmed: number;
  corrected: number;
  pending: number;
  containers: number;
}

function totalsFor(days: readonly CollectionDay[], filters: OverviewFilters): Totals {
  const totals: Totals = {
    observed: 0,
    relevant: 0,
    likelyHate: 0,
    selectedHate: 0,
    confirmed: 0,
    corrected: 0,
    pending: 0,
    containers: 0,
  };

  const containersByPlatform = new Map<string, number>();

  for (const day of days) {
    if (!day.collected) {
      continue;
    }
    for (const row of day.platforms) {
      if (!isSelectedPlatform(row.platform, filters)) {
        continue;
      }
      totals.observed += row.observed;
      totals.relevant += row.relevant;
      totals.likelyHate += row.likelyHate;
      totals.selectedHate += selectedHate(row, filters);
      totals.confirmed += row.reviewConfirmed;
      totals.corrected += row.reviewCorrected;
      totals.pending += row.reviewPending;
      containersByPlatform.set(row.platform, row.containers);
    }
  }

  totals.containers = [...containersByPlatform.values()].reduce((sum, count) => sum + count, 0);
  return totals;
}

function baselineWindow(
  document: CollectionDocument,
  window: { from: string; to: string },
): readonly CollectionDay[] {
  const dates = document.days.map((day) => day.date);
  const startIndex = dates.indexOf(window.from);
  const endIndex = dates.indexOf(window.to);
  if (startIndex <= 0) {
    return [];
  }
  const length = endIndex - startIndex + 1;
  return document.days.slice(Math.max(0, startIndex - length), startIndex);
}

function metricsFor(
  document: CollectionDocument,
  window: { from: string; to: string },
  days: readonly CollectionDay[],
  filters: OverviewFilters,
): OverviewMetric[] {
  const totals = totalsFor(days, filters);
  const previous = baselineWindow(document, window);
  const previousTotals = totalsFor(previous, filters);

  const rate = rateOf(totals.selectedHate, totals.relevant);
  const previousRate = rateOf(previousTotals.selectedHate, previousTotals.relevant);
  const reviewed = totals.confirmed + totals.corrected;
  const windowDays = days.length;
  const collectedDays = days.filter((day) => day.collected).length;

  const hasSelection =
    (filters.hateTypes?.length ?? 0) +
      (filters.severityBands?.length ?? 0) +
      (filters.reviewStates?.length ?? 0) >
    0;

  return [
    {
      id: 'observed',
      label: 'Items collected',
      definition:
        'Comments successfully collected and stored from the monitored containers in this window. Not a sample of any whole platform.',
      unit: 'count',
      value: totals.observed,
      numerator: null,
      denominator: null,
      isModelOnly: false,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'relevant',
      label: 'Muslim-related items',
      definition:
        'Items the relevance stage judged to be about Muslims or Islam. Relevance is not harm: this count includes neutral and supportive speech.',
      unit: 'count',
      value: totals.relevant,
      numerator: totals.relevant,
      denominator: totals.observed,
      isModelOnly: true,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'likely-hate',
      label: hasSelection ? 'Likely hate, selected slice' : 'Classified as likely hate',
      definition: hasSelection
        ? 'Items classified as likely anti-Muslim hate that also match the current classification selection. Narrowing the selection narrows this count, not the denominator.'
        : 'Items classified as likely anti-Muslim hate by the model. A classification is a proposal for review, not a finding.',
      unit: 'count',
      value: totals.selectedHate,
      numerator: totals.selectedHate,
      denominator: totals.relevant,
      isModelOnly: true,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'rate',
      label: 'Likely hate rate',
      definition:
        'Items classified as likely anti-Muslim hate, divided by Muslim-related items in the same window and scope.',
      unit: 'rate',
      value: rate,
      numerator: totals.selectedHate,
      denominator: totals.relevant,
      isModelOnly: true,
      insufficientVolume: rate === null,
      changeVsBaseline:
        rate === null || previousRate === null
          ? null
          : {
              absolute: rate - previousRate,
              percent: previousRate === 0 ? 0 : ((rate - previousRate) / previousRate) * 100,
              baselineLabel: `previous ${String(windowDays)} days`,
            },
    },
    {
      id: 'reviewed',
      label: 'Confirmed by review',
      definition:
        'Likely-hate classifications a trained reviewer has confirmed, out of those a reviewer has looked at. Corrections are counted separately and never overwrite the model.',
      unit: 'count',
      value: totals.confirmed,
      numerator: totals.confirmed,
      denominator: reviewed,
      isModelOnly: false,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'pending',
      label: 'Awaiting review',
      definition:
        'Likely-hate classifications no person has assessed yet. Every figure on this page that is marked model-only rests partly on these.',
      unit: 'count',
      value: totals.pending,
      numerator: totals.pending,
      denominator: totals.likelyHate,
      isModelOnly: false,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'severe',
      label: 'Severity 2 or 3 share',
      definition:
        'Likely-hate items the model placed in the two higher severity bands, out of all likely-hate items in scope.',
      unit: 'rate',
      value: rateOf(severityTotals(days, filters, ['2', '3']), totals.likelyHate),
      numerator: severityTotals(days, filters, ['2', '3']),
      denominator: totals.likelyHate,
      isModelOnly: true,
      insufficientVolume: totals.likelyHate < MIN_DENOMINATOR,
      changeVsBaseline: null,
    },
    {
      id: 'coverage-days',
      label: 'Days collected',
      definition:
        'Days in this window with a successful collection run. A missing day is drawn as a gap, never as a zero.',
      unit: 'count',
      value: collectedDays,
      numerator: collectedDays,
      denominator: windowDays,
      isModelOnly: false,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
  ];
}

function severityTotals(
  days: readonly CollectionDay[],
  filters: OverviewFilters,
  bands: readonly string[],
): number {
  let total = 0;
  for (const day of days) {
    if (!day.collected) {
      continue;
    }
    for (const row of day.platforms) {
      if (!isSelectedPlatform(row.platform, filters)) {
        continue;
      }
      total += sumValues(row.severity, bands);
    }
  }
  return total;
}

interface BreakdownInput {
  id: string;
  label: string;
  dimension: OverviewBreakdown['dimension'];
  definition: string;
  denominatorLabel: string;
  rows: readonly { key: string; label: string; count: number; denominator: number }[];
}

function breakdown(input: BreakdownInput): OverviewBreakdown {
  return {
    id: input.id,
    label: input.label,
    dimension: input.dimension,
    definition: input.definition,
    total: input.rows.reduce((sum, row) => sum + row.count, 0),
    countLabel: 'items classified as likely anti-Muslim hate',
    denominatorLabel: input.denominatorLabel,
    rows: input.rows.map((row) => ({
      key: row.key,
      label: row.label,
      count: row.count,
      denominator: row.denominator,
      rate: rateOf(row.count, row.denominator),
    })),
  };
}

function breakdownsFor(
  document: CollectionDocument,
  days: readonly CollectionDay[],
  filters: OverviewFilters,
): OverviewBreakdown[] {
  const totals = totalsFor(days, filters);

  return [
    breakdown({
      id: 'by-type',
      label: 'Type of harm',
      dimension: 'hate_type',
      definition:
        'The primary type recorded for each likely-hate item. Real classification is multi-label; this axis shows one label per item, so the shares describe the dominant framing rather than every element present.',
      denominatorLabel: 'Muslim-related items',
      rows: document.hateTypes.map((type) => ({
        key: type,
        label: hateTypeLabel(type),
        count: countBy(days, filters, (row) => row.types[type] ?? 0),
        denominator: totals.relevant,
      })),
    }),
    breakdown({
      id: 'by-severity',
      label: 'Severity band',
      dimension: 'severity',
      definition:
        'The severity the model assigned, from 0 for borderline to 3 for severe. Severity is a model judgement and carries the same review caveat as the classification itself.',
      denominatorLabel: 'Muslim-related items',
      rows: document.severityBands.map((band) => ({
        key: band,
        label: severityLabel(band),
        count: countBy(days, filters, (row) => row.severity[band] ?? 0),
        denominator: totals.relevant,
      })),
    }),
    breakdown({
      id: 'by-platform',
      label: 'Source platform',
      dimension: 'platform',
      definition:
        'Where the items were collected. Volumes differ because the monitored containers differ, so these shares describe this sample and not the platforms.',
      denominatorLabel: 'Muslim-related items on that platform',
      rows: document.platforms
        .filter((platform) => isSelectedPlatform(platform.platform, filters))
        .map((platform) => ({
          key: platform.platform,
          label: platformLabel(platform.platform),
          count: countBy(days, { ...filters, platforms: [platform.platform] }, (row) =>
            selectedHate(row, filters),
          ),
          denominator: countBy(
            days,
            { ...filters, platforms: [platform.platform] },
            (row) => row.relevant,
          ),
        })),
    }),
    breakdown({
      id: 'by-review',
      label: 'Review state',
      dimension: 'review_state',
      definition:
        'How far each likely-hate classification has travelled through human review. A correction appends a decision; it never overwrites the model.',
      denominatorLabel: 'likely-hate classifications',
      rows: [
        { key: 'confirmed', count: totals.confirmed },
        { key: 'corrected', count: totals.corrected },
        { key: 'pending', count: totals.pending },
      ].map((entry) => ({
        key: entry.key,
        label: reviewLabel(entry.key),
        count: entry.count,
        denominator: totals.likelyHate,
      })),
    }),
  ];
}

function countBy(
  days: readonly CollectionDay[],
  filters: OverviewFilters,
  pick: (row: CollectionPlatformDay) => number,
): number {
  let total = 0;
  for (const day of days) {
    if (!day.collected) {
      continue;
    }
    for (const row of day.platforms) {
      if (!isSelectedPlatform(row.platform, filters)) {
        continue;
      }
      total += pick(row);
    }
  }
  return total;
}

export function deriveOverview(document: CollectionDocument, filters: OverviewFilters): Overview {
  const window = resolveWindow(document, filters);
  const days = daysInWindow(document, window);
  const totals = totalsFor(days, filters);
  const gaps = days.filter((day) => !day.collected).map((day) => day.date);

  const selectedPlatforms = document.platforms.filter((platform) =>
    isSelectedPlatform(platform.platform, filters),
  );

  const warnings = gaps.map(
    (date) =>
      `Collection failed on ${date}, so that day appears as a gap. Figures in this window exclude it rather than counting it as zero.`,
  );

  return {
    window: { from: window.from, to: window.to, timezone: document.available.timezone },
    coverage: {
      sources: selectedPlatforms.map((platform) => platform.platform),
      itemsObserved: totals.observed,
      itemsRelevant: totals.relevant,
      lastSuccessfulRun: document.lastSuccessfulRun,
      warnings,
      containersMonitored: totals.containers,
      containerLabel: selectedPlatforms.map((platform) => platform.containerLabel).join(' and '),
    },
    applied: appliedFilters(document, filters),
    metrics: metricsFor(document, window, days, filters),
    daily: dailySeries(days, filters),
    breakdowns: breakdownsFor(document, days, filters),
  };
}

export function deriveFilterOptions(document: CollectionDocument): FilterOptions {
  const allDays = document.days;
  const none: OverviewFilters = {};

  return {
    available: document.available,
    defaultWindowDays: document.defaultWindowDays,
    platforms: document.platforms.map((platform) => ({
      value: platform.platform,
      label: platformLabel(platform.platform),
      count: countBy(allDays, { platforms: [platform.platform] }, (row) => row.likelyHate),
    })),
    hateTypes: document.hateTypes.map((type) => ({
      value: type,
      label: hateTypeLabel(type),
      count: countBy(allDays, none, (row) => row.types[type] ?? 0),
    })),
    severityBands: document.severityBands.map((band) => ({
      value: band,
      label: severityLabel(band),
      count: countBy(allDays, none, (row) => row.severity[band] ?? 0),
    })),
    reviewStates: REVIEW_STATES.map((state) => ({
      value: state,
      label: reviewLabel(state),
      count: countBy(allDays, none, (row) =>
        state === 'confirmed'
          ? row.reviewConfirmed
          : state === 'corrected'
            ? row.reviewCorrected
            : row.reviewPending,
      ),
    })),
  };
}
