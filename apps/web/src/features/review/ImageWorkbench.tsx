import { useCallback, useState, type ChangeEvent } from 'react';

import { InfoTip } from '@/components/ui/InfoTip';

import { ImageLabelForm } from './ImageLabelForm';
import { ModelTestPanel } from './ModelTestPanel';

import styles from './ImageWorkbench.module.css';

type ImagePath = 'label' | 'test';

/**
 * The two things a person does with an image here, kept apart on purpose.
 *
 * Labelling records a training annotation; testing records nothing. Collapsing
 * them into one screen would mean someone trying the model out to see what it
 * does could leave a training label behind without having chosen to, so the
 * choice is made before the upload rather than after it.
 */
export function ImageWorkbench() {
  const [path, setPath] = useState<ImagePath>('label');

  const handlePathChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setPath(event.currentTarget.value as ImagePath);
  }, []);

  return (
    <section className={styles.card} aria-labelledby="image-workbench-heading">
      <div className={styles.headingRow}>
        <h2 id="image-workbench-heading" className={styles.heading}>
          Work with an image
        </h2>
        <InfoTip label="Work with an image">
          Two separate paths. Labelling saves a training annotation. Testing saves nothing and
          exists only to show what the classifier does.
        </InfoTip>
      </div>

      <fieldset className={styles.paths}>
        <legend className={styles.pathsLegend}>What do you want to do?</legend>

        <label className={styles.path} htmlFor="image-path-label">
          <input
            id="image-path-label"
            type="radio"
            name="image-path"
            value="label"
            checked={path === 'label'}
            onChange={handlePathChange}
          />
          <span>
            <span className={styles.pathName}>Label an image</span>
            <span className={styles.pathDetail}>
              Record a training annotation for later fine-tuning. This is saved.
            </span>
          </span>
        </label>

        <label className={styles.path} htmlFor="image-path-test">
          <input
            id="image-path-test"
            type="radio"
            name="image-path"
            value="test"
            checked={path === 'test'}
            onChange={handlePathChange}
          />
          <span>
            <span className={styles.pathName}>Test the model</span>
            <span className={styles.pathDetail}>
              See how the classifier reads an image, in ordinary words. Nothing is saved.
            </span>
          </span>
        </label>
      </fieldset>

      {path === 'label' ? <ImageLabelForm /> : <ModelTestPanel />}
    </section>
  );
}
