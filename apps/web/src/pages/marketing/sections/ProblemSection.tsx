import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { FeedThreadFigure } from '@/components/marketing/FeedThreadFigure';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import styles from './NarrativeSection.module.css';

export function ProblemSection() {
  return (
    <MarketingSection tone="light" id="the-problem" hasWatermark>
      <div className={styles.layout}>
        <Reveal>
          <div className={styles.header}>
            <SectionLabel ordinal="01">The problem</SectionLabel>
            <DisplayHeading
              level={2}
              upright="Each comment already matters."
              accent="The feed will not keep it."
            />
            <div className={styles.prose}>
              <p>
                A reply under a news video, a joke in a thread, a meme that travels further than the
                post it mocks: any one of these can already wound. Nothing about being a single
                remark makes the harm smaller, or less real, for the person who meets it.
              </p>
              <p>
                The feed treats that remark as disposable. By the time the next item arrives, the
                last one is gone. What remains is a feeling, not a record anyone can return to, name
                carefully, or sit with long enough to understand.
              </p>
              <p>
                Communities are left carrying that feeling without a way to look back at what
                produced it. <span className={styles.emphasis}>That</span> is the loss no refresh
                will repair, and the reason a public observatory has work to do.
              </p>
            </div>
          </div>
        </Reveal>

        <div className={styles.aside}>
          <Reveal delayMs={90}>
            <FeedThreadFigure />
          </Reveal>
        </div>
      </div>
    </MarketingSection>
  );
}
