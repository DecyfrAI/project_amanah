import { useCallback, useEffect, useState, type ChangeEvent, type DragEvent } from 'react';

import { ApiRequestError, readDataMode, type ImageClassification } from '@/api';
import { EvidencePreview } from '@/features/reports/EvidencePreview';
import { EVIDENCE_MAX_BYTES, validateEvidenceFile } from '@/features/reports/evidence-file';
import { useClassifyEvidence } from '@/features/reports/useClassifyEvidence';

import {
  HATE_TYPE_PLAIN,
  confidenceSentence,
  relevanceSentence,
  severitySentence,
  stanceSentence,
} from './model-test-copy';

import styles from './ModelTestPanel.module.css';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'That image could not be checked. Try another file.';
}

/**
 * Try the classifier on an image and read the answer in ordinary words.
 *
 * Nothing is stored. The file is held in this tab for the preview and released
 * when the panel is cleared, and no label, prediction, or catalog row is
 * written: this path exists to show what the model does, not to collect
 * anything. Labelling is the other path, and it is deliberately separate.
 */
export function ModelTestPanel() {
  const classify = useClassifyEvidence();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    return () => {
      if (previewUrl !== null) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const applyFile = useCallback(
    (chosen: File): void => {
      try {
        const valid = validateEvidenceFile(chosen);
        setFileError(null);
        setFile(valid);
        setPreviewUrl((current) => {
          if (current !== null) {
            URL.revokeObjectURL(current);
          }
          return URL.createObjectURL(valid);
        });
        classify.mutate({ image_filename: valid.name, image_byte_size: valid.size });
      } catch (error) {
        setFile(null);
        classify.reset();
        setPreviewUrl((current) => {
          if (current !== null) {
            URL.revokeObjectURL(current);
          }
          return null;
        });
        setFileError(error instanceof Error ? error.message : 'That image could not be used.');
      }
    },
    [classify],
  );

  const handleFile = useCallback(
    (event: ChangeEvent<HTMLInputElement>): void => {
      const chosen = event.currentTarget.files?.[0];
      if (chosen !== undefined) {
        applyFile(chosen);
      }
    },
    [applyFile],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>): void => {
      event.preventDefault();
      setIsDragging(false);
      const chosen = event.dataTransfer.files[0];
      if (chosen !== undefined) {
        applyFile(chosen);
      }
    },
    [applyFile],
  );

  const handleClear = useCallback((): void => {
    setFile(null);
    setFileError(null);
    classify.reset();
    setPreviewUrl((current) => {
      if (current !== null) {
        URL.revokeObjectURL(current);
      }
      return null;
    });
  }, [classify]);

  return (
    <div className={styles.panel}>
      <p className={styles.lead}>
        Upload an image and see how the classifier reads it, in ordinary words. Nothing is saved:
        the file stays in this tab, no label is recorded, and the image is not added to any
        catalogue.
      </p>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="model-test-image">
          Image to test
        </label>
        <div
          className={isDragging ? `${styles.dropzone} ${styles.dropzoneActive}` : styles.dropzone}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <p className={styles.dropTitle}>Drop an image here</p>
          <p className={styles.hint} id="model-test-hint">
            PNG, JPEG or WebP, under {Math.round(EVIDENCE_MAX_BYTES / 1024)} KB. Nothing leaves this
            tab and nothing is stored.
          </p>
          <input
            id="model-test-image"
            className={styles.file}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleFile}
            aria-describedby="model-test-hint"
          />
        </div>
      </div>

      {fileError !== null && (
        <p className={styles.error} role="alert">
          {fileError}
        </p>
      )}
      {classify.isPending && <p className={styles.pending}>Asking the model.</p>}
      {classify.isError && (
        <p className={styles.error} role="alert">
          {errorMessage(classify.error)}
        </p>
      )}

      {previewUrl !== null && file !== null && (
        <EvidencePreview src={previewUrl} filename={file.name} />
      )}

      {classify.data !== undefined && (
        <>
          <PlainResult result={classify.data} />
          <button type="button" className={styles.clear} onClick={handleClear}>
            Clear and try another
          </button>
        </>
      )}
    </div>
  );
}

/**
 * The same classification the reviewer card shows, in ordinary sentences.
 *
 * The rehearsal notice is not a disclaimer to scroll past. In fixture mode the
 * stub never opens the file: it picks a stored example from a hash of the
 * filename, so renaming an image changes the answer and two different images
 * with one name give the same one. Someone trying the model would otherwise
 * reasonably read this as their image having been analysed.
 */
function PlainResult({ result }: { result: ImageClassification }) {
  const mode = readDataMode();
  const isRehearsal = result.data_mode === 'fixture' || result.data_mode === 'fallback';

  return (
    <section className={styles.result} aria-labelledby="model-test-result-heading">
      <h3 id="model-test-result-heading" className={styles.resultHeading}>
        What the model made of it
      </h3>

      {isRehearsal && (
        <div className={styles.rehearsal} role="note">
          <p className={styles.rehearsalTitle}>This is a rehearsal, not a reading of your image</p>
          <p className={styles.rehearsalBody}>
            {mode === 'fallback'
              ? 'The live model could not be reached, so this fell back to the fixture stub. '
              : ''}
            In fixture mode the stub does not open the file. It picks a stored example from the
            file's name, so renaming an image changes the answer and two images with the same name
            give the same one. The wording below shows the shape of a real reply. It is not a
            judgment about the image you chose.
          </p>
        </div>
      )}

      <p className={styles.headline}>{stanceSentence(result.stance)}</p>

      <ul className={styles.points}>
        <li>{relevanceSentence(result.relevance)}</li>
        <li>{confidenceSentence(result.confidence_tier)}</li>
        <li>{severitySentence(result.severity)}</li>
        {result.hate_types.length > 0 && (
          <li>
            What it flagged: {result.hate_types.map((type) => HATE_TYPE_PLAIN[type]).join('; ')}.
          </li>
        )}
      </ul>

      {result.rationale !== '' && (
        <p className={styles.rationale}>
          <span className={styles.rationaleLabel}>Its reasoning:</span> {result.rationale}
        </p>
      )}

      <p className={styles.score}>
        Model score {result.score.toFixed(2)} from {result.model_name} {result.model_version}. A
        score is how the model ranks its own output. It is not a probability that the answer is
        correct.
      </p>

      <p className={styles.caveat}>
        Whatever it said, this is a proposal and not a finding. No person has looked at it, and
        Amanah does not treat a classification as true until one has. Nothing here was saved.
      </p>
    </section>
  );
}
