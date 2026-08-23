import { DisplayHeading } from '@/components/marketing/DisplayHeading';
import { EyebrowPill } from '@/components/marketing/EyebrowPill';
import { ButtonAnchor, ButtonLink } from '@/components/ui/Button';
import { useParallax } from '@/hooks/useParallax';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useRotatingPhrase } from '@/hooks/useRotatingPhrase';

import styles from './HeroSection.module.css';

const HEADLINE_STEM = 'Understand how anti-Muslim hate';

/**
 * The clauses the headline cycles through.
 *
 * Each names something the product can actually evidence or that the brand
 * documents already claim, how narratives change, how repeated exposure dulls
 * a community's response, how a pattern escapes notice. None of them assert
 * anything the data would not support.
 */
const HEADLINE_CLAUSES = [
  'evolves online.',
  'grows in hearts.',
  'desensitizes youth.',
  'hardens into narrative.',
  'slips past notice.',
] as const;

/**
 * What a screen reader announces in place of the rotating headline. Written out
 * rather than joined from the clauses, so it reads as one sentence instead of
 * five fragments run together.
 */
const HEADLINE_ACCESSIBLE_NAME =
  'Understand how anti-Muslim hate evolves online, grows in hearts, desensitizes youth, ' +
  'hardens into narrative, and slips past notice.';

/** Backdrop travels at a third of scroll speed, which reads as depth. */
const PARALLAX_SPEED = 0.32;

export function HeroSection() {
  const backdropRef = useParallax<HTMLDivElement>(PARALLAX_SPEED);
  const prefersReducedMotion = useReducedMotion();
  const { phrase, index } = useRotatingPhrase(HEADLINE_CLAUSES);

  return (
    <section className={styles.hero}>
      <div className={styles.backdrop} ref={backdropRef} aria-hidden="true">
        {/*
          Under reduced motion the poster frame stands in for the clip entirely.
          An autoplaying video is precisely what that preference exists to
          prevent, and the still carries the same image.
        */}
        {prefersReducedMotion ? (
          <img className={styles.media} src="/media/hero-poster.jpg" alt="" />
        ) : (
          <video
            className={styles.media}
            src="/media/hero.mp4"
            poster="/media/hero-poster.jpg"
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
          />
        )}
        <div className={styles.aurora} />
      </div>
      <div className={styles.scrim} aria-hidden="true" />

      <div className={styles.content}>
        <EyebrowPill>A collective moral responsibility</EyebrowPill>

        {/*
          The accessible name states the stem and every clause once, and never
          changes; the rotating clause is visual only.
        */}
        <div>
          <DisplayHeading
            level={1}
            isHero
            upright={HEADLINE_STEM}
            accessibleName={HEADLINE_ACCESSIBLE_NAME}
            accent={
              <span className={styles.rotator}>
                <span key={index} className={styles.rotatorPhrase}>
                  {phrase}
                </span>
              </span>
            }
          />
        </div>

        <p className={styles.subhead}>
          Our deen is a light we see by, an amanah placed in our care, and a duty we hold together.
          This project turns that care into trends, narratives, context and reviewable reports,
          without profiling people.
        </p>

        <div className={styles.actions}>
          <ButtonLink variant="primary" to="/signup">
            Sign up
          </ButtonLink>
          <ButtonAnchor variant="secondary" href="#what-it-does">
            See how it works
          </ButtonAnchor>
        </div>
      </div>

      <a className={styles.chevron} href="#the-problem">
        Scroll
        <svg
          className={styles.chevronIcon}
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          aria-hidden="true"
        >
          <path d="M4 7l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </a>
    </section>
  );
}
