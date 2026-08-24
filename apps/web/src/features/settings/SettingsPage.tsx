import { useCallback, useState, type ChangeEvent } from 'react';

import { MockupNotice } from '@/components/ui/MockupNotice';
import { requestWorkspaceTour } from '@/features/tour/tour-storage';
import { usePageTitle } from '@/hooks/usePageTitle';

import { useMediaPreference } from './media-preference';
import { DENSITY_OPTIONS, SAMPLE_ROWS, type TableDensity } from './mock';

import styles from './SettingsPage.module.css';

/**
 * Per-person preferences, not administrative controls.
 *
 * The media-display preference is real and persisted: it is stored on the
 * authenticated profile and applies across Explorer, Reports, and every other
 * approved image surface (PA-01). Table density is still page-local and says
 * so, since a toggle that appears to save and does not is worse than one that
 * admits it.
 */
export function SettingsPage() {
  usePageTitle('Settings');

  const { blurMedia, setBlurMedia, isSaving, saveError } = useMediaPreference();
  const [density, setDensity] = useState<TableDensity>('comfortable');

  const handleBlurChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>): void => {
      setBlurMedia(event.currentTarget.checked);
    },
    [setBlurMedia],
  );

  const handleDensityChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setDensity(event.currentTarget.value as TableDensity);
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
        <p className={styles.lead}>
          Preferences that change how photographs are shown, and how dense the research views are.
          These are your own choices, not administrative controls, and nothing here changes what
          anyone else sees. Comment wording is shown in full.
        </p>
      </header>

      {/*
       * Scoped deliberately. The media preference below is real and persisted,
       * so a blanket "nothing here is live" notice would now be the misleading
       * claim. Only the density sample table is an illustration.
       */}
      <MockupNotice
        detail="The sample table under Table density is written from local constants to show row height."
        controlsNote="Content safety, above, is a real preference saved to your profile."
      />

      <div className={styles.layout}>
        <div className={styles.primary}>
          <section className={styles.card} aria-labelledby="safety-heading">
            <h2 id="safety-heading" className={styles.sectionHeading}>
              Content safety
            </h2>
            <fieldset className={styles.fieldset}>
              <legend className={styles.legend}>What you see by default</legend>

              <div className={styles.checkRow}>
                <input
                  className={styles.checkbox}
                  id="blur-media"
                  name="blur-media"
                  type="checkbox"
                  checked={blurMedia}
                  onChange={handleBlurChange}
                  disabled={isSaving}
                  aria-describedby="blur-media-hint"
                />
                <div className={styles.checkText}>
                  <label className={styles.checkLabel} htmlFor="blur-media">
                    Blur media by default
                  </label>
                  <p className={styles.hint} id="blur-media-hint">
                    Off by default: images are shown. Turn this on and images stay blurred behind a
                    deliberate reveal. Every image keeps its own Show and Hide control either way.
                    Text is never blurred by this setting.
                  </p>
                </div>
              </div>
            </fieldset>

            <output className={styles.summary} aria-live="polite">
              {blurMedia
                ? 'Media stays blurred until you show it.'
                : 'Media appears without blurring.'}
            </output>

            {saveError !== null && (
              <p className={styles.error} role="alert">
                {saveError}
              </p>
            )}

            <p className={styles.pending}>
              This choice is saved to your profile, so it survives a refresh and a new session, and
              applies immediately across Explorer, Review, Insights, and Reports. It changes how
              images are displayed only: it never changes who may read an item, and it does not
              affect text redaction.
            </p>
          </section>

          <section className={styles.card} aria-labelledby="theme-heading">
            <h2 id="theme-heading" className={styles.sectionHeading}>
              Theme
            </h2>
            <p className={styles.pending}>
              Light and dark are already working, and the toggle lives at the foot of the sidebar
              next to your name. That one is remembered between visits. It is not repeated here,
              because two controls for one preference is how they drift apart.
            </p>
          </section>

          <section className={styles.card} aria-labelledby="help-heading">
            <h2 id="help-heading" className={styles.sectionHeading}>
              Help
            </h2>
            <p className={styles.pending}>
              Replay the workspace tour that walks the sidebar, every tab including Profile and
              Settings, the Overview figures, and Ask Amanah. The same control sits in the
              bottom-right Tour button.
            </p>
            <button type="button" className={styles.tourButton} onClick={requestWorkspaceTour}>
              Replay workspace tour
            </button>
          </section>
        </div>

        <section className={styles.card} aria-labelledby="density-heading">
          <h2 id="density-heading" className={styles.sectionHeading}>
            Table density
          </h2>
          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>Row height in research tables</legend>
            {DENSITY_OPTIONS.map((option) => (
              <div className={styles.checkRow} key={option.value}>
                <input
                  className={styles.radio}
                  id={`density-${option.value}`}
                  name="density"
                  type="radio"
                  value={option.value}
                  checked={density === option.value}
                  onChange={handleDensityChange}
                  aria-describedby={`density-${option.value}-hint`}
                />
                <div className={styles.checkText}>
                  <label className={styles.checkLabel} htmlFor={`density-${option.value}`}>
                    {option.label}
                  </label>
                  <p className={styles.hint} id={`density-${option.value}-hint`}>
                    {option.detail}
                  </p>
                </div>
              </div>
            ))}
          </fieldset>

          <table className={density === 'compact' ? styles.tableCompact : styles.table}>
            <caption className={styles.caption}>
              Sample rows, written for this preview. A model score is a score on the model's own
              scale, not a proportion and not a measure of certainty.
            </caption>
            <thead>
              <tr>
                <th scope="col">Item</th>
                <th scope="col">Platform</th>
                <th scope="col">Proposed label</th>
                <th scope="col">Model score</th>
              </tr>
            </thead>
            <tbody>
              {SAMPLE_ROWS.map((row) => (
                <tr key={row.id}>
                  <th scope="row" className={styles.rowHeader}>
                    {row.id}
                  </th>
                  <td>{row.platform}</td>
                  <td>{row.proposedLabel}</td>
                  <td className={styles.numeric}>{row.modelScore.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p className={styles.pending}>
            The preview above changes with your choice. The Explorer does not yet, and the choice is
            not saved between visits.
          </p>
        </section>
      </div>
    </div>
  );
}
