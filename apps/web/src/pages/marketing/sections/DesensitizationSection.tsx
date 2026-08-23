import { DashboardPreview } from '@/components/marketing/DashboardPreview';
import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import styles from './NarrativeSection.module.css';

export function DesensitizationSection() {
  return (
    <MarketingSection tone="light" id="why-it-matters" hasWatermark>
      <div className={styles.layout}>
        <Reveal>
          <div className={styles.header}>
            <SectionLabel ordinal="03">Why it matters</SectionLabel>
            <DisplayHeading level={2} upright="Why longitudinal" accent="monitoring matters." />
            <div className={styles.prose}>
              <p>
                Narratives return. Rates move. Collection days go dark. None of that can be read
                from a single sitting, and none of it can be reconstructed from memory without
                asking the same people to keep rereading the harm.
              </p>
              <p>
                Holding the longer view has usually meant searching for, reading and saving harmful
                material, work that falls on the people most affected by it. No one should have to
                keep that archive in their own head, or reopen it, simply to show that something is
                happening again.
              </p>
              <p>
                Project Amanah keeps a bounded, authorized sample over time so that work does not
                have to be done in private, over and over. Context stays with each item. Narratives
                are measured. Change becomes a structured, reviewable record, and a missed
                collection day is drawn as a gap rather than a quiet zero. That is the view
                policymakers and researchers have been missing: not a screenshot from one site, but
                a cohesive record across the sources we monitor, held long enough to see whether a
                narrative is returning.
              </p>
              <p>
                <span className={styles.emphasis}>
                  That record is itself an amanah: it must be collected with restraint, interpreted
                  carefully and handled with respect for the people represented within it.
                </span>
              </p>
            </div>
          </div>
        </Reveal>

        <div className={styles.aside}>
          <Reveal delayMs={90}>
            <DashboardPreview />
          </Reveal>
        </div>
      </div>
    </MarketingSection>
  );
}
