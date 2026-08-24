import {
  useCallback,
  useEffect,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from 'react';

import { ApiRequestError, hateTypeLabel, type HateType } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';
import { EvidenceClassification } from '@/features/reports/EvidenceClassification';
import { EvidencePreview } from '@/features/reports/EvidencePreview';
import { EVIDENCE_MAX_BYTES, validateEvidenceFile } from '@/features/reports/evidence-file';
import { useClassifyEvidence } from '@/features/reports/useClassifyEvidence';

import styles from './ImageLabelForm.module.css';

const HATE_TYPES: readonly HateType[] = [
  'animosity',
  'derogation',
  'dehumanization',
  'exclusion',
  'threat_or_incitement',
  'collective_blame',
  'other',
];

interface SavedLabel {
  readonly filename: string;
  readonly byteSize: number;
  readonly classification: 'likely_hate' | 'not_hate';
  readonly hateTypes: readonly HateType[];
  readonly severity: number;
  readonly note: string;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'That image could not be classified. Try another file.';
}

/**
 * Upload a research image and save a training label.
 *
 * The request is filename and size only. There is no author, handle, or other
 * personal field. A later importer can send this record to fine-tune storage.
 */
export function ImageLabelForm() {
  const classify = useClassifyEvidence();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [hateTypes, setHateTypes] = useState<readonly HateType[]>([]);
  const [severity, setSeverity] = useState('2');
  const [classification, setClassification] = useState<'likely_hate' | 'not_hate'>('likely_hate');
  const [note, setNote] = useState('');
  const [saved, setSaved] = useState<readonly SavedLabel[]>([]);
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
        classify.mutate({
          image_filename: valid.name,
          image_byte_size: valid.size,
        });
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

  const handleClassification = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    setClassification(event.currentTarget.value as 'likely_hate' | 'not_hate');
  }, []);

  const handleSeverity = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    setSeverity(event.currentTarget.value);
  }, []);

  const handleNote = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setNote(event.currentTarget.value);
  }, []);

  const handleType = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    const value = event.currentTarget.value as HateType;
    setHateTypes((current) =>
      current.includes(value) ? current.filter((entry) => entry !== value) : [...current, value],
    );
  }, []);

  const handleSave = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      if (file === null || hateTypes.length === 0) {
        return;
      }
      setSaved((current) => [
        ...current,
        {
          filename: file.name,
          byteSize: file.size,
          classification,
          hateTypes,
          severity: Number(severity),
          note: note.trim(),
        },
      ]);
    },
    [classification, file, hateTypes, note, severity],
  );

  return (
    <section className={styles.card} aria-labelledby="image-label-heading">
      <div className={styles.headingRow}>
        <h2 id="image-label-heading" className={styles.heading}>
          Label an image
        </h2>
        <InfoTip label="Label an image">
          This label is a training annotation. It does not overwrite a model proposal, and it is
          never applied automatically.
        </InfoTip>
      </div>
      <p className={styles.lead}>
        Upload a research image to classify and label it for later fine-tuning. The image is
        uploaded to Amanah and stored privately; only you can read it, and location and camera
        metadata are removed before storage. Do not enter a name, handle, or other personal detail,
        and do not upload personal photographs.
      </p>

      <form className={styles.form} onSubmit={handleSave}>
        <fieldset className={styles.upload}>
          <legend className={styles.uploadLegend}>Image</legend>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="research-image">
              Research image
            </label>
            <div
              className={
                isDragging ? `${styles.dropzone} ${styles.dropzoneActive}` : styles.dropzone
              }
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <p className={styles.dropTitle}>Drop a research image here</p>
              <p className={styles.hint} id="research-image-hint">
                PNG, JPEG or WebP, under {Math.round(EVIDENCE_MAX_BYTES / 1024)} KB. The file stays
                in this tab.
              </p>
              <input
                id="research-image"
                className={styles.file}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleFile}
                aria-describedby="research-image-hint"
              />
            </div>
          </div>

          {fileError !== null && (
            <p className={styles.error} role="alert">
              {fileError}
            </p>
          )}
          {classify.isPending && (
            <p className={styles.pending}>Checking the image. Pixels stay in this tab.</p>
          )}
          {classify.isError && (
            <p className={styles.error} role="alert">
              {errorMessage(classify.error)}
            </p>
          )}

          {previewUrl !== null && file !== null && (
            <EvidencePreview src={previewUrl} filename={file.name} />
          )}
          {classify.data !== undefined && <EvidenceClassification result={classify.data} />}
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend className={styles.legend}>Your label</legend>
          <p className={styles.hint}>
            This is a training annotation. It does not overwrite the model proposal above.
          </p>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="label-classification">
              Classification
            </label>
            <select
              id="label-classification"
              className={styles.control}
              value={classification}
              onChange={handleClassification}
            >
              <option value="likely_hate">Classified as likely anti-Muslim hate</option>
              <option value="not_hate">Classified as not hate</option>
            </select>
          </div>

          <fieldset className={styles.types}>
            <legend className={styles.legend}>Hate types</legend>
            {HATE_TYPES.map((type) => (
              <label key={type} className={styles.check}>
                <input
                  type="checkbox"
                  value={type}
                  checked={hateTypes.includes(type)}
                  onChange={handleType}
                />
                {hateTypeLabel(type)}
              </label>
            ))}
          </fieldset>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="label-severity">
              Severity
            </label>
            <select
              id="label-severity"
              className={styles.control}
              value={severity}
              onChange={handleSeverity}
            >
              <option value="0">0, borderline</option>
              <option value="1">1, low</option>
              <option value="2">2, moderate</option>
              <option value="3">3, severe</option>
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="label-note">
              Form note
            </label>
            <textarea
              id="label-note"
              className={styles.control}
              rows={3}
              value={note}
              onChange={handleNote}
              placeholder="Describe layout and form. Do not paste slogans or personal details."
            />
          </div>
        </fieldset>

        <button
          type="submit"
          className={styles.primaryAction}
          disabled={file === null || hateTypes.length === 0}
        >
          Save training label
        </button>
      </form>

      {saved.length > 0 && (
        <ul className={styles.saved}>
          {saved.map((label) => (
            <li key={`${label.filename}-${label.byteSize}`}>
              {label.filename} · {label.byteSize.toLocaleString('en')} bytes ·{' '}
              {label.classification === 'likely_hate' ? 'likely hate' : 'not hate'} · severity{' '}
              {label.severity}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
