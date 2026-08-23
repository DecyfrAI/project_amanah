import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { MarketingSection } from '@/components/marketing/MarketingSection';
import { Reveal } from '@/components/marketing/Reveal';
import { SectionLabel } from '@/components/marketing/SectionLabel';

import styles from './AmanahSection.module.css';
import narrative from './NarrativeSection.module.css';

/**
 * The verses the project's name and conduct rest on.
 *
 * Quoted in full rather than paraphrased, so a reader meets the text itself
 * rather than our reading of it. Translation is Hilali-Khan (The Noble
 * Qur'an), and each card links through to the verse on quran.com so the
 * wording can be checked against the source.
 */
/**
 * Ornament for each verse card, echoing its theme.
 *
 * Decorative: the theme is already stated in text beside it, so the icon is
 * hidden from assistive technology rather than duplicating that label. Drawn in
 * `currentColor` so it takes the card's own ground.
 */
function ScalesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M12 4v16M8 20h8M5 8h14M12 5.5 5 8l-2.4 5a3.6 3.6 0 0 0 4.8 0L5 8m7-2.5L19 8l2.4 5a3.6 3.6 0 0 1-4.8 0L19 8" />
    </svg>
  );
}

function LampIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M12 2.5v2M12 21h0M9.5 21h5M8 8.5h8l2 6.5a6 6 0 0 1-12 0l2-6.5ZM10 8.5V6h4v2.5" />
      <path d="M12 12v4" />
    </svg>
  );
}

function ClaspIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M9.5 12a4 4 0 1 1 0-6.5h2a4 4 0 0 1 0 6.5M14.5 12a4 4 0 1 1 0 6.5h-2a4 4 0 0 1 0-6.5" />
    </svg>
  );
}

const VERSES = [
  {
    reference: 'Surah An-Nisa 4:58',
    url: 'https://quran.com/4/58',
    theme: 'Trust and justice',
    Icon: ScalesIcon,
    text: 'Verily, Allah commands that you should render back the trusts to those to whom they are due; and that when you judge between men, you judge with justice. Verily, how excellent is the teaching which He (Allah) gives you! Truly, Allah is Ever All-Hearer, All-Seer.',
  },
  {
    reference: 'Surah Ali \u2018Imran 3:104',
    url: 'https://quran.com/3/104',
    theme: 'Enjoining good',
    Icon: LampIcon,
    text: 'Let there arise out of you a group of people inviting to all that is good (Islam), enjoining Al-Ma\u2018ruf (all that Islam orders one to do) and forbidding Al-Munkar (all that Islam has forbidden). And it is they who are the successful.',
  },
  {
    reference: 'Surah At-Tawbah 9:71',
    url: 'https://quran.com/9/71',
    theme: 'Mutual protection',
    Icon: ClaspIcon,
    text: 'The believers, men and women, are Auliya\u2019 (helpers, supporters, friends, protectors) of one another; they enjoin Al-Ma\u2018ruf, and forbid Al-Munkar; they perform As-Salat, and give the Zakat, and obey Allah and His Messenger. Allah will have His Mercy on them. Surely Allah is All-Mighty, All-Wise.',
  },
] as const;

export function AmanahSection() {
  return (
    <MarketingSection tone="dark" id="our-philosophy" hasWatermark>
      <Reveal>
        <div className={narrative.header}>
          <SectionLabel ordinal="04">Our philosophy</SectionLabel>
          <DisplayHeading
            level={2}
            upright="The deen is a light."
            accent="An amanah we carry together."
          />

          <div className={narrative.prose}>
            <p>
              <span className={narrative.emphasis}>Amānah</span> means a trust, something placed in
              your care that you will be asked about. The deen is that kind of trust: the light we
              see our lives by, and the light our mark holds. We are entrusted with the care of one
              another, and called to stand for what is good and resist what causes harm.
            </p>
            <p>
              Protecting it is not a duty anyone else is going to carry on our behalf. That
              protective concern has a name, <span className={narrative.emphasis}>ghayrah</span>,
              and losing it is not neutrality. It is a loss.
            </p>
            <p>
              Our deen and our communities are among the things placed in our care. When they are
              demeaned and we feel nothing, something has gone that is worth naming. The name of
              this project is a reminder of that duty, not a claim that we have already discharged
              it.
            </p>
          </div>
        </div>
      </Reveal>

      <ul className={styles.verses}>
        {VERSES.map((verse, index) => (
          <li key={verse.reference}>
            <Reveal delayMs={index * 90}>
              <figure className={styles.verse}>
                <p className={styles.verseTheme}>
                  <span className={styles.verseIcon}>
                    <verse.Icon />
                  </span>
                  {verse.theme}
                </p>
                <blockquote className={styles.verseText}>{verse.text}</blockquote>
                <figcaption>
                  <a
                    className={styles.verseReference}
                    href={verse.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {verse.reference}
                  </a>
                </figcaption>
              </figure>
            </Reveal>
          </li>
        ))}
      </ul>

      <p className={styles.translationNote}>
        Translation: Hilali-Khan, The Noble Qur&rsquo;an. Each reference links to the verse on
        quran.com.
      </p>

      <dl className={styles.glossary}>
        <div className={styles.term}>
          <dt className={styles.termName}>Ghayrah</dt>
          <dd className={styles.termDefinition}>
            Disciplined protective concern for the deen and community, the refusal to normalize or
            grow numb to harm. It is governed by truth, mercy, wisdom and justice. It is never
            anger, possessiveness, or licence to police any individual.
          </dd>
        </div>
        <div className={styles.term}>
          <dt className={styles.termName}>Enjoining good, forbidding wrong</dt>
          <dd className={styles.termDefinition}>
            Responsible witness and principled response: making harm visible, preserving reviewable
            evidence, and supporting correction. It is not coercion, vigilantism, automated
            punishment, or judgment of anyone&rsquo;s faith.
          </dd>
        </div>
      </dl>
    </MarketingSection>
  );
}
