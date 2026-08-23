import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { PathVisuals } from '@/components/marketing/PathVisuals';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import styles from './NarrativeSection.module.css';

/**
 * The online path the observatory exists to sit beside: anonymity, narrower
 * rooms, and the question of whether a careful record can inform policy.
 *
 * This is framing, not a finding. Nothing here claims a comment caused an
 * attack. The wording stays "coincides with" and "has been documented."
 */
export function PathSection() {
  return (
    <MarketingSection tone="dark" id="the-path" hasWatermark>
      <div className={styles.layout}>
        <Reveal>
          <div className={styles.header}>
            <SectionLabel ordinal="02">The path online</SectionLabel>
            <DisplayHeading
              level={2}
              upright="A handle is not a face."
              accent="The room still teaches someone."
            />
            <div className={styles.prose}>
              <p>
                People who would never say these things in a shop, a school, or a mosque become
                bolder when the only name in the room is a handle. Anonymity does not invent the
                hostility. It lowers the cost of saying it out loud, and of finding others who will
                cheer it on.
              </p>
              <p>
                Some of those rooms stay on ordinary sites: a reply under a news video, a joke in a
                thread. Others drift. A person starts on a well known site and, over time, follows
                the narrower doors into smaller boards that reward cruelty. Imageboards such as
                4chan and 8chan appear often in that reporting as destinations. This page does not
                send anyone there. Naming them is a warning about a path, not a map.
              </p>
              <p>
                Those narrower rooms have sat next to real harm. Mosque attacks, school attacks, and
                assaults on Muslim people have, in documented public cases, been preceded by time in
                spaces like that. Hostility aimed at one community often travels with hostility
                aimed at others. Coincidence is not proof that a comment caused an attack. It is a
                reason not to treat the comment as disposable.
              </p>
              <p>
                So the question is practical.{' '}
                <span className={styles.emphasis}>
                  What if the speech and the patterns could be tracked, understood, and placed next
                  to events in the same window?
                </span>{' '}
                A scoped record, with denominators and with missing days drawn as gaps, is something
                a community organization, a newsroom, or a public body can carry into a conversation
                about policy. It is not a verdict on a platform or a people. It is a way not to rely
                on memory.
              </p>
            </div>
          </div>
        </Reveal>

        <div className={styles.aside}>
          <Reveal delayMs={90}>
            <PathVisuals />
          </Reveal>
        </div>
      </div>
    </MarketingSection>
  );
}
