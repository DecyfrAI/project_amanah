/**
 * Local constants behind the Reports mockup.
 *
 * The snapshots below describe reports nobody prepared. They exist so the layout
 * of a snapshot list can be reviewed, and they are labelled as illustrations on
 * screen. Report creation belongs to `POST /v1/research-reports`, which this
 * frontend cannot call yet, so nothing here implies a report exists to open.
 */

import type { StatusIndicator } from '@/components/ui/StatusPill';

export interface ScopeField {
  readonly id: string;
  readonly label: string;
  /** The value the control shows while it is inert. */
  readonly value: string;
  readonly options: readonly string[];
}

export const SCOPE_FIELDS: readonly ScopeField[] = [
  {
    id: 'platform',
    label: 'Platform',
    value: 'All configured platforms',
    options: [
      'All configured platforms',
      'YouTube',
      'Reddit',
      'Bluesky',
      'Mastodon (single instance)',
      'Open datapack (source shown as N/A)',
    ],
  },
  {
    id: 'severity',
    label: 'Severity band',
    value: 'Any band, 0 to 3',
    options: ['Any band, 0 to 3', '1 and above', '2 and above', '3 only'],
  },
  {
    id: 'review-state',
    label: 'Review state',
    value: 'Model classification and human review',
    options: [
      'Model classification and human review',
      'Reviewed by a person only',
      'Awaiting review only',
      'Corrected by a reviewer only',
    ],
  },
];

export const SCOPE_DATE_RANGE = {
  from: '2026-08-09',
  to: '2026-08-22',
} as const;

export interface ReportSection {
  readonly id: string;
  readonly name: string;
  /** What the section holds, and the constraint that keeps it defensible. */
  readonly detail: string;
}

export const REPORT_SECTIONS: readonly ReportSection[] = [
  {
    id: 'executive-summary',
    name: 'Executive summary',
    detail:
      'Two paragraphs describing what the monitored sample showed in this window. Written from stored figures, never producing a figure of its own.',
  },
  {
    id: 'selected-filters',
    name: 'Selected filters, frozen',
    detail:
      'The exact scope the figures describe, captured when the report is created so the report cannot drift from the query behind it.',
  },
  {
    id: 'coverage',
    name: 'Coverage and denominators',
    detail:
      'Sources, containers monitored, items observed, and every day collection failed, listed as gaps rather than folded into the totals.',
  },
  {
    id: 'trend',
    name: 'Trend charts with tabular equivalents',
    detail:
      'Daily rate per source, each chart followed by the same numbers as a table and a text summary, with missing days drawn as gaps.',
  },
  {
    id: 'findings',
    name: 'Narrative findings',
    detail:
      'Changes worth attention, in non-causal wording: a rise coincides with an event, it is never caused by one.',
  },
  {
    id: 'evidence',
    name: 'Redacted evidence references',
    detail:
      'Opaque item references with container context and redacted excerpts. No handles, no reconstructed slurs, no person-level detail.',
  },
  {
    id: 'methodology',
    name: 'Methodology',
    detail:
      'How items were collected, what the relevance gate does, and what the taxonomy version means for the labels in the report.',
  },
  {
    id: 'model-disclosure',
    name: 'Model disclosure',
    detail:
      'Model name, version, prompt version, and confidence tiers, with the reminder that a score is a model score and not a measure of certainty.',
  },
  {
    id: 'limitations',
    name: 'Limitations',
    detail:
      'What this report cannot support, at full weight: a bounded sample is not a platform, a country, or a group of people.',
  },
];

export interface ReportSnapshot {
  readonly id: string;
  readonly title: string;
  readonly window: string;
  readonly filters: string;
  readonly createdAt: string;
  readonly indicator: StatusIndicator;
  readonly statusLabel: string;
  /** What a reader has to know before quoting this snapshot. */
  readonly caveat: string;
}

export const REPORT_SNAPSHOTS: readonly ReportSnapshot[] = [
  {
    id: 'rep_5b21c8',
    title: 'Planning decision coverage, two weeks',
    window: '9 August 2026 to 22 August 2026',
    filters: 'YouTube and Reddit, any severity, model and reviewed',
    createdAt: '22 August 2026, 08:40 UTC',
    indicator: 'ok',
    statusLabel: 'Prepared',
    caveat: 'Covers 214 containers, 1,208 classified items, and 14 of 14 days collected.',
  },
  {
    id: 'rep_9c4470',
    title: 'Threat and incitement band, one month',
    window: '18 July 2026 to 18 August 2026',
    filters: 'All configured platforms, band 3 only, reviewed only',
    createdAt: '18 August 2026, 17:05 UTC',
    indicator: 'degraded',
    statusLabel: 'Prepared with a coverage gap',
    caveat:
      'The Mastodon connector failed on 5 of the 31 days. Those days are reported as gaps, so the totals describe 26 collected days.',
  },
  {
    id: 'rep_1f7de3',
    title: 'Open datapack baseline, historical rows',
    window: '1 January 2024 to 31 December 2024',
    filters: 'Open datapack only, any severity, awaiting review only',
    createdAt: '11 August 2026, 12:22 UTC',
    indicator: 'absent',
    statusLabel: 'Trend section is a gap',
    caveat:
      'A one-off import has no daily collection, so the trend section reports no daily rate rather than a flat line at zero.',
  },
];
