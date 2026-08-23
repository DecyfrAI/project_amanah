import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { ExpandingPanels, type ExpandingPanel } from '@/components/marketing/ExpandingPanels';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import narrative from './NarrativeSection.module.css';
import styles from './WhatItDoesSection.module.css';

/**
 * The analyst's path through the product, in the order they actually walk it.
 *
 * Ordered as a workflow rather than a feature list, because the value is in the
 * sequence: a number is only trustworthy if you can reach the records under it,
 * and a record only matters if a person can correct it.
 */
const PANELS: readonly ExpandingPanel[] = [
  {
    id: 'coverage',
    name: 'Coverage',
    headline: 'See what the sample actually covers',
    body: 'Start with the coverage strip: which sources ran, how many records were collected, when the last successful run finished, and what failed. Connections names the authorized sources and any open datapack provenance. Every rate on the page is scoped by this, and a failed collection shows as a gap rather than a zero.',
    outcome: 'You know what the numbers describe before you read them',
  },
  {
    id: 'trends',
    name: 'Trends',
    headline: 'Track the rate over time',
    body: 'The daily likely-hate rate against its own baseline, with the relevant-item denominator in every tooltip. Spikes are annotated, and volume is charted separately so a busy collection day is never mistaken for a worse one.',
    outcome: 'A change you can point at, with the denominator attached',
  },
  {
    id: 'narratives',
    name: 'Narratives',
    headline: 'See which narratives are moving',
    body: 'Classified items roll up into a fixed taxonomy, collective blame, demographic threat, incompatibility, criminality, cultural contamination, ranked by share and by change against the previous window.',
    outcome: 'The specific frame that is growing, not just that something is',
  },
  {
    id: 'explorer',
    name: 'Explorer',
    headline: 'Search the records behind a figure',
    body: 'Click any chart element and the Explorer opens with those exact filters in the URL. Keyword search with autocomplete, filters for source, type, severity and review state, and a preview of every row. Image posts show form, filename, size and annotation metadata rather than a comment.',
    outcome: 'The specific records supporting the aggregate you clicked',
  },
  {
    id: 'insights',
    name: 'Insights',
    headline: 'Keep a snapshot, including image evidence',
    body: 'Start a snapshot from a figure or a day so colleagues can attach notes to the same finding. Image posts in the window appear with their metadata: filename, byte size, form note, and the dataset annotation, kept separate from the model proposal. Comments stay comments. This is not a public forum.',
    outcome: 'A cited finding you can return to, with the counts attached',
  },
  {
    id: 'review',
    name: 'Review',
    headline: 'Correct the model, and label an image',
    body: 'Open an item to see its context, the model label with its score, and the provenance. Confirm, correct, or skip. A decision appends beside the original prediction. The research image catalog lives here, blurred until revealed. You can also upload an image to label it for later fine-tuning: filename and size only, no personal fields.',
    outcome: 'An auditable human judgment, with the model output preserved',
  },
  {
    id: 'ask',
    name: 'Ask',
    headline: 'Talk to the figures, with the window attached',
    body: 'Ask Amanah takes the active date range and filters as context. Starter questions cover the rate, the trend, coverage, an explorer entry, current events, and news that coincides with the window. Numbers come from the same computed figures the dashboard shows. It is not allowed to invent a rate or treat a collection gap as zero.',
    outcome: 'A grounded answer about this sample, not a generated statistic',
  },
  {
    id: 'lessons',
    name: 'Lessons',
    headline: 'Study the path, after you sign in',
    body: 'Eight short research modules, documented case studies, and a resource list with crisis lines. The catalog is part of the signed-in workspace. Marketing no longer opens it as a public dashboard page.',
    outcome: 'Education and support without treating a visitor as a reviewer',
  },
  {
    id: 'report',
    name: 'Reports',
    headline: 'Export something you can defend',
    body: 'The report builder inherits your active filters and freezes them, along with coverage, methodology, model versions and limitations. Prepare a platform report for a person to send. Amanah never submits one. Print-optimized HTML plus an aggregate CSV of exactly what the charts showed.',
    outcome: 'A scoped report that states its own limits',
  },
];

/** Stated plainly, because the boundaries are what make the tool trustworthy. */
const BOUNDARIES = [
  'No profiling of individuals',
  'No inferring anyone’s religion',
  'No automated takedowns or reports',
  'No claim that events caused anything',
  'No scraping, authorized APIs only',
  'No population-level prevalence claims',
] as const;

export function WhatItDoesSection() {
  return (
    <MarketingSection tone="light" id="what-it-does" hasWatermark>
      <Reveal>
        <div className={narrative.header}>
          <SectionLabel ordinal="05">What it does</SectionLabel>
          <DisplayHeading level={2} upright="Not another feed." accent="An analytics tool." />

          <div className={`${narrative.prose} ${styles.intro}`}>
            <p>
              Project Amanah is an observatory, not a timeline. It collects permitted public content
              from approved sources, separates what is <em>about</em> Muslims from what is{' '}
              <em>against</em> them, and turns the result into something a researcher or community
              organization can actually reason about.
            </p>
            <p>
              The goal is one platform for the sources we are allowed to watch. Anti-Muslim hate is
              scattered across sites, comment threads, and news desks. Amanah brings that material
              together so policymakers, researchers, and anyone working from data can see the
              broadest, most cohesive picture the monitored sample can support, follow how the
              pattern evolves over time, and study how it takes root. A news event or a remark may
              coincide with a movement in the figures. The observatory does not treat that as proof
              of a cause.
            </p>
          </div>
        </div>
      </Reveal>

      <ExpandingPanels panels={PANELS} />

      <div className={styles.boundary}>
        <p className={styles.boundaryLabel}>What it deliberately does not do</p>
        <ul className={styles.boundaryList}>
          {BOUNDARIES.map((boundary) => (
            <li key={boundary} className={styles.boundaryItem}>
              <span className={styles.boundaryMark} aria-hidden="true">
                ·
              </span>
              {boundary}
            </li>
          ))}
        </ul>
      </div>
    </MarketingSection>
  );
}
