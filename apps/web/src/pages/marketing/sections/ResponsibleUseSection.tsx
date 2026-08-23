import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { FlipCard } from '@/components/marketing/FlipCard';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import narrative from './NarrativeSection.module.css';
import styles from './ResponsibleUseSection.module.css';

/**
 * The safeguards.
 *
 * `summary` is the refusal; `detail` is how it is actually held to. Splitting
 * them across the two faces of a card keeps the claim short enough to scan while
 * the substantiation stays one press away.
 */
const SAFEGUARDS = [
  {
    name: 'Access',
    summary: 'We collect only what we are permitted to collect.',
    detail:
      'Documented official APIs and permitted feeds, nothing else. When access is unavailable the connector says so plainly, there is no scraping fallback, and no coverage is implied that we do not have.',
  },
  {
    name: 'Identity',
    summary: 'We watch sources and communities. Never people.',
    detail:
      'No profiles, no rankings, no person-level search, and no inference of anyone’s religion. Author identifiers are pseudonymized with a keyed hash that is never joined across platforms.',
  },
  {
    name: 'Relevance',
    summary: 'Being about Muslims is not the same as being against them.',
    detail:
      'Muslim vocabulary, Islamic symbols, Arabic text and religious discussion make an item relevant to the sample. They never, on their own, make it harmful. Relevance and stance are separate model stages for exactly this reason.',
  },
  {
    name: 'Scope',
    summary: 'Every number describes our sample, and says so.',
    detail:
      'Rates arrive with their numerator, denominator, and collection coverage. A failed collection renders as a gap, never as a zero. Nothing here is a claim about prevalence across a platform or a population.',
  },
  {
    name: 'Causation',
    summary: 'Things that happen together are not things that cause each other.',
    detail:
      'When a change coincides with reporting about an event, the interface says it coincided. Establishing cause needs a study design this one does not have, and the language never pretends otherwise.',
  },
  {
    name: 'Restraint',
    summary: 'We keep as little as the work allows.',
    detail:
      'Minimal retention, private encrypted storage, access logging, and a deletion path that propagates. Demonstrations use synthetic material rather than real people’s words.',
  },
] as const;

export function ResponsibleUseSection() {
  return (
    <MarketingSection tone="light" id="responsible-use" hasWatermark>
      <Reveal>
        <div className={narrative.header}>
          <SectionLabel ordinal="07">Responsible use</SectionLabel>
          <DisplayHeading level={2} upright="What we refuse" accent="to build." />

          <div className={narrative.prose}>
            <p>
              A tool that watches for hate can become a tool that watches people. The difference is
              not good intentions, it is which capabilities exist at all. These are the ones we have
              deliberately left out.
            </p>
          </div>
        </div>
      </Reveal>

      <div className={styles.safeguards}>
        {SAFEGUARDS.map((safeguard) => (
          <FlipCard
            key={safeguard.name}
            name={safeguard.name}
            summary={safeguard.summary}
            detail={safeguard.detail}
          />
        ))}
      </div>

      <div className={styles.correction}>
        <p className={styles.correctionHeading}>If we have something wrong</p>
        <p className={styles.safeguardBody}>
          Classifications are machine-generated until a person reviews them, and people get things
          wrong too. Every reviewer decision stays visible in the audit history beside the original
          model output. The request path for a correction or deletion is stated with the
          methodology, where the numbers are accounted for.
        </p>
      </div>
    </MarketingSection>
  );
}
