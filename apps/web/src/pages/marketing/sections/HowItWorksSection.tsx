import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';
import { StageCarousel, type CarouselStage } from '@/components/marketing/StageCarousel';

import styles from './HowItWorksSection.module.css';
import { STAGE_IMAGE_CREDITS } from './stageImageCredits';
import narrative from './NarrativeSection.module.css';

/**
 * The evidence lifecycle from the planning documents.
 *
 * `detail` states the constraint that makes each stage trustworthy rather than
 * restating what the stage does. Image alt text describes the artwork itself,
 * since the artwork illustrates the stage rather than diagramming it.
 */
const STAGES: readonly CarouselStage[] = [
  {
    id: 'capture',
    name: 'Capture',
    summary:
      'Collect the smallest unit that carries the finding, plus enough thread and source context to interpret it.',
    detail:
      'Authorized APIs only. Every item records the query that found it, the collection run, and when it was observed, so any figure can be traced back to how it was gathered.',
    imageAlt: 'A camera lens resting in a dim interior, focused.',
  },
  {
    id: 'classify',
    name: 'Classify',
    summary:
      'Establish relevance first, then stance, then type and severity, each with a confidence band.',
    detail:
      'Relevance and hate are separate judgments. Muslim vocabulary makes an item relevant; it never, on its own, makes it harmful. Uncertain cases abstain rather than guess.',
    imageAlt: 'Coloured pencils laid out in ordered, overlapping rows.',
  },
  {
    id: 'contextualize',
    name: 'Contextualize',
    summary:
      'Attach the narrative, the monitored community, and any contemporaneous reporting from the same period.',
    detail:
      'Stated as association, never as cause. An observational sample bounded by our own queries cannot establish that an event made anything happen.',
    imageAlt: 'A world map marked with coloured pins casting long shadows.',
  },
  {
    id: 'review',
    name: 'Human review',
    summary:
      'A trained reviewer confirms, corrects, rejects, or asks for more context before anything counts as settled.',
    detail:
      'Decisions append to the record. The original model output is preserved beside every correction, so the history stays auditable, and so a reviewer can be wrong too.',
    imageAlt: 'A printed page annotated by hand, with reading glasses resting on it.',
  },
  {
    id: 'report',
    name: 'Learn and report',
    summary:
      'Corrections feed evaluation, and the filtered view becomes a report that carries its own limits with it.',
    detail:
      'Every export states the sources, communities, dates and filters behind it, plus what was missed. A report describes a bounded sample, never a whole platform.',
    imageAlt: 'An open ledger, its entries recorded by hand in ruled columns.',
  },
];

export function HowItWorksSection() {
  return (
    <MarketingSection tone="dark" id="how-it-works" hasWatermark>
      <Reveal>
        <div className={narrative.header}>
          <SectionLabel ordinal="06">How it works</SectionLabel>
          <DisplayHeading level={2} upright="The trust," accent="made operational." />

          <div className={narrative.prose}>
            <p>
              Five stages, each of which leaves a record of what it did and why. The pipeline
              narrows a bounded sample down to the few items that genuinely need a person to look at
              them.
            </p>
          </div>
        </div>
      </Reveal>

      <StageCarousel stages={STAGES} label="The five stages of the evidence lifecycle" />

      <p className={styles.credits}>
        Photographs:{' '}
        {STAGE_IMAGE_CREDITS.map((credit, index) => (
          <span key={credit.stage}>
            {index > 0 && '; '}
            <a href={credit.url} target="_blank" rel="noopener noreferrer">
              {credit.title}
            </a>{' '}
            by {credit.creator} ({credit.license})
          </span>
        ))}
      </p>

      <p className={styles.humanNote}>
        A machine can narrow the field. It cannot decide what is hateful, and it is never allowed to
        act on its own guess.
      </p>
    </MarketingSection>
  );
}
