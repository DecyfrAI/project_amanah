import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import styles from './MethodologySection.module.css';
import narrative from './NarrativeSection.module.css';

/**
 * Disclosure of how the numbers are produced.
 *
 * Every planning document requires the sampling statement, taxonomy, model and
 * dataset versions, AI tooling, and known limitations to be public. This is the
 * public-safe form of that; the authenticated methodology page carries the
 * version detail that changes per release.
 */
const GROUPS = [
  {
    heading: 'What is collected',
    entries: [
      {
        term: 'Sources',
        definition:
          'Public content from documented official APIs, against a registry of approved queries and communities. Where access is unavailable the connector is disabled and says so, there is no scraping fallback.',
      },
      {
        term: 'Sampling',
        definition:
          'Discovery uses neutral topic terms, not slur lists. Searching for hate and then reporting the result as prevalence would preselect the answer. High-risk queries, when used to find evaluation cases, are labelled and excluded from ordinary rate comparisons.',
      },
      {
        term: 'Denominator',
        definition:
          'The likely-hate rate is likely-hate items divided by Muslim-relevant items, not by everything collected, and not by everything on a platform.',
      },
    ],
  },
  {
    heading: 'How labels are decided',
    entries: [
      {
        term: 'Two stages, not one',
        definition:
          'Relevance is established before stance. An item can be highly relevant and entirely benign; ordinary Muslim speech, reporting, theological debate and counterspeech are explicit non-hate classes, not edge cases.',
      },
      {
        term: 'Taxonomy',
        definition:
          'Animosity, derogation, dehumanization, exclusion, threat, and collective blame, each with a severity from 0 to 3. Multi-label, so shares can exceed 100 per cent.',
      },
      {
        term: 'Uncertainty',
        definition:
          'Each label carries its own calibrated confidence. Below threshold the model abstains and routes to review rather than guessing. Everything is marked Model only until a person has looked at it.',
      },
    ],
  },
  {
    heading: 'Tools and data',
    entries: [
      {
        term: 'AI disclosure',
        definition:
          'Classification runs locally or through explicitly authorized hosted inference. Generated summaries are labelled machine-generated, cite the figures they rest on, and are checked against those figures before display.',
      },
      {
        term: 'Third-party transfer',
        definition:
          'Real harmful content and personal data are never sent to an external model without a recorded authorization covering that transfer. The default is to refuse, and it is enforced in code rather than by policy.',
      },
      {
        term: 'Imagery on this page',
        definition:
          'Stage photographs are public-domain, CC0 and CC BY works, each credited with its creator, source and licence. The closing photograph is a generated architectural illustration. No real collected content, and no identifiable person, appears anywhere on this page.',
      },
    ],
  },
] as const;

/**
 * Stated at full weight rather than in small print. If the caveats are hard to
 * read, the numbers above them are being oversold.
 */
const LIMITATIONS = [
  'This is a bounded sample, not a census. It cannot tell you how much anti-Muslim hate exists.',
  'Coverage varies by source and by day. A drop in the chart may be a drop in collection.',
  'Models miss coded language, irony, and dialect, and they misread quoted speech and reclaimed terms.',
  'English only at present. Non-English items are stored and marked, not classified.',
  'Event associations are temporal coincidences. Nothing here establishes that an event caused anything.',
  'Reviewer judgment is human judgment. It is auditable and correctable, not infallible.',
] as const;

export function MethodologySection() {
  return (
    <MarketingSection tone="dark" id="methodology" hasWatermark>
      <Reveal>
        <div className={narrative.header}>
          <SectionLabel ordinal="08">Methodology</SectionLabel>
          <DisplayHeading level={2} upright="How the numbers" accent="are actually made." />

          <div className={narrative.prose}>
            <p>
              A figure is only worth as much as the account of how it was produced. This is that
              account, in the shortest honest form.
            </p>
          </div>
        </div>
      </Reveal>

      <div className={styles.groups}>
        {GROUPS.map((group) => (
          <div key={group.heading} className={styles.group}>
            <h3 className={styles.groupHeading}>{group.heading}</h3>
            <dl className={styles.entries}>
              {group.entries.map((entry) => (
                <div key={entry.term}>
                  <dt className={styles.term}>{entry.term}</dt>
                  <dd className={styles.definition}>{entry.definition}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>

      <div className={styles.limitations} id="limitations">
        <h3 className={styles.limitationsHeading}>What this cannot tell you</h3>
        <ul className={styles.limitationList}>
          {LIMITATIONS.map((limitation) => (
            <li key={limitation} className={styles.limitation}>
              <span className={styles.limitationMark} aria-hidden="true">
                ·
              </span>
              {limitation}
            </li>
          ))}
        </ul>
      </div>

      <p className={styles.contact} id="corrections">
        If you are represented in this data and something is wrong, you can request a correction or
        deletion. Reviewer decisions and the original model output both stay in the audit history,
        so a correction is visible rather than silent.
      </p>
    </MarketingSection>
  );
}
