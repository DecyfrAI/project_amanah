/**
 * Editorial copy describing what a research report contains.
 *
 * This is documentation of the report's structure, not data: report creation
 * and reading go through `/v1/research-reports` in `ResearchReportPanel`. The
 * inert scope form and the illustrative snapshot list that used to live here
 * were removed when that flow was connected.
 */

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
