import { Logo } from '@/brand/Logo';
import { ButtonLink } from '@/components/ui/Button';
import { useParallax } from '@/hooks/useParallax';

import { MARKETING_SECTIONS } from './marketing-sections';

import styles from './MarketingFooter.module.css';

/** Modest, the photograph already has room to travel and the zoom is separate. */
const PARALLAX_SPEED = 0.16;

const CURRENT_YEAR = new Date().getFullYear();

export function MarketingFooter() {
  const closingParallaxRef = useParallax<HTMLDivElement>(PARALLAX_SPEED);

  return (
    <footer className={styles.footer}>
      <section className={styles.closing} aria-labelledby="closing-heading">
        <div className={styles.closingMedia}>
          <div className={styles.closingParallax} ref={closingParallaxRef}>
            <img
              className={styles.closingImage}
              src="/media/closing-mosque.webp"
              alt=""
              width={1024}
              height={576}
              loading="lazy"
              decoding="async"
            />
          </div>
          <span className={styles.closingScrim} aria-hidden="true" />
        </div>

        <div className={styles.closingContent}>
          <h2 id="closing-heading" className={styles.closingHeading}>
            Carry the trust <span className={styles.closingAccent}>with care.</span>
          </h2>
          <p className={styles.closingBody}>
            If you work with a community organization, a newsroom, or a research group and this
            would help you, we would like to hear from you.
          </p>
          <div className={styles.closingActions}>
            <ButtonLink variant="primary" to="/signup">
              Sign up
            </ButtonLink>
            <ButtonLink variant="secondary" to="/login">
              Log in
            </ButtonLink>
          </div>
        </div>
      </section>

      <div className={styles.inner}>
        <div className={styles.columns}>
          <div className={styles.brandColumn}>
            <Logo variant="inverse" size="large" />
            <p className={styles.statement}>
              Guarding the deen is a responsibility we hold together, and no one should have to hold
              it alone.
            </p>
          </div>

          <nav className={styles.sectionNav} aria-label="Page sections">
            <h2 className={styles.navHeading}>On this page</h2>
            <ul className={styles.linkList}>
              {MARKETING_SECTIONS.map((section) => (
                <li key={section.href}>
                  <a className={styles.link} href={section.href}>
                    {section.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className={styles.baseline}>
          <p>
            © {CURRENT_YEAR} Project Amanah, Monitoring Anti-Muslim Hate Online, The Harvest
            Anti-Muslim Hate Hackathon
          </p>
          <p className={styles.builtBy}>
            Built by{' '}
            <a
              className={styles.builtByLink}
              href="https://decyfrai.com/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Decyfr AI
            </a>
          </p>
        </div>
      </div>

      {/* Repeating silhouette along the base. Ornament only. */}
      <div className={styles.silhouette} aria-hidden="true">
        <div className={styles.silhouetteStrip} />
      </div>
    </footer>
  );
}
