import {
  useCallback,
  useEffect,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from 'react';
import { useSearchParams } from 'react-router-dom';

import { ApiRequestError } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';

import { EvidenceClassification } from './EvidenceClassification';
import { EvidencePreview } from './EvidencePreview';
import { validateEvidenceFile } from './evidence-file';
import { PlatformReportPaths } from './PlatformReportPaths';
import { isReportPlatform, REPORT_PLATFORM_OPTIONS } from './prepare-report-draft';
import { ReportDraftPreview } from './ReportDraftPreview';
import { useClassifyEvidence } from './useClassifyEvidence';
import { usePrepareReportDraft } from './usePrepareReportDraft';

import styles from './PlatformReportDraft.module.css';

type EvidenceMode = 'image' | 'describe';

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'The draft could not be prepared. Check the details and try again.';
}

/**
 * Assisted platform-report form (F-S14).
 *
 * A person uploads a screenshot or describes what they saw. The mock model
 * formats wording for an official report form. Amanah never sends it.
 */
export function PlatformReportDraft() {
  const [params] = useSearchParams();
  const prepare = usePrepareReportDraft();
  const classify = useClassifyEvidence();
  const platformParam = params.get('platform');
  const itemParam = params.get('item');
  const initialPlatform =
    platformParam !== null && isReportPlatform(platformParam) ? platformParam : '';

  const [platform, setPlatform] = useState<string>(initialPlatform);
  const [evidenceMode, setEvidenceMode] = useState<EvidenceMode>('image');
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [contentUrl, setContentUrl] = useState('');
  const [urlError, setUrlError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    return () => {
      if (previewUrl !== null) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handlePlatform = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    setPlatform(event.currentTarget.value);
  }, []);

  const handleEvidenceMode = useCallback(
    (event: ChangeEvent<HTMLInputElement>): void => {
      const next = event.currentTarget.value === 'describe' ? 'describe' : 'image';
      setEvidenceMode(next);
      if (next === 'describe') {
        setFile(null);
        setFileError(null);
        classify.reset();
        setPreviewUrl((current) => {
          if (current !== null) {
            URL.revokeObjectURL(current);
          }
          return null;
        });
      }
    },
    [classify],
  );

  const applyChosenFile = useCallback(
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
        setFileError(error instanceof Error ? error.message : 'That screenshot could not be used.');
      }
    },
    [classify],
  );

  const handleFile = useCallback(
    (event: ChangeEvent<HTMLInputElement>): void => {
      const chosen = event.currentTarget.files?.[0];
      if (chosen === undefined) {
        return;
      }
      applyChosenFile(chosen);
    },
    [applyChosenFile],
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
        applyChosenFile(chosen);
      }
    },
    [applyChosenFile],
  );

  const handleNote = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setNote(event.currentTarget.value);
  }, []);

  const handleUrl = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setContentUrl(event.currentTarget.value);
    setUrlError(null);
  }, []);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      if (!isReportPlatform(platform)) {
        return;
      }
      const trimmedUrl = contentUrl.trim();
      if (trimmedUrl.length > 0 && !/^https?:\/\/.+/i.test(trimmedUrl)) {
        setUrlError('Start the URL with http:// or https://. Amanah will not fetch it.');
        return;
      }
      const trimmedNote = note.trim();
      const sourceItem = itemParam?.trim() ?? '';

      prepare.mutate({
        platform,
        has_image: evidenceMode === 'image' && file !== null,
        ...(trimmedNote.length > 0 ? { reporter_note: trimmedNote } : {}),
        ...(trimmedUrl.length > 0 ? { content_url: trimmedUrl } : {}),
        ...(file !== null ? { image_filename: file.name, image_byte_size: file.size } : {}),
        ...(sourceItem.length > 0 ? { source_item_id: sourceItem.slice(0, 64) } : {}),
      });
    },
    [contentUrl, evidenceMode, file, itemParam, note, platform, prepare],
  );

  return (
    <section className={styles.card} aria-labelledby="prepare-report-heading">
      <div className={styles.headingRow}>
        <h2 id="prepare-report-heading" className={styles.sectionHeading}>
          Prepare a platform report
        </h2>
        <InfoTip label="Prepare a platform report">
          Amanah formats wording you can paste into the official report form. It never submits the
          report to a platform.
        </InfoTip>
      </div>
      <p className={styles.lead}>
        Upload a screenshot or describe what you saw. Choose the platform. Generate wording for that
        platform&apos;s official report form. You copy or download it, then send the form yourself.
        This prepares a platform report. It does not notify a government authority.
      </p>
      {itemParam !== null && itemParam.length > 0 && (
        <p className={styles.itemNote}>
          Started from review item {itemParam}. That is a content reference, not a person.
        </p>
      )}

      <form className={styles.form} onSubmit={handleSubmit}>
        <fieldset className={styles.fieldset}>
          <legend className={styles.legend}>Evidence</legend>
          <div className={styles.choices}>
            <label className={styles.choice}>
              <input
                type="radio"
                name="evidence-mode"
                value="image"
                checked={evidenceMode === 'image'}
                onChange={handleEvidenceMode}
              />
              Upload a screenshot
            </label>
            <label className={styles.choice}>
              <input
                type="radio"
                name="evidence-mode"
                value="describe"
                checked={evidenceMode === 'describe'}
                onChange={handleEvidenceMode}
              />
              No image, I will describe it
            </label>
          </div>
          {evidenceMode === 'image' && (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="evidence-file">
                Screenshot
              </label>
              <div
                className={
                  isDragging ? `${styles.dropzone} ${styles.dropzoneActive}` : styles.dropzone
                }
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <p className={styles.dropTitle}>Drop a screenshot here</p>
                <p className={styles.hint} id="evidence-file-hint">
                  PNG, JPEG or WebP, under 5120 KB. The file stays in this tab.
                </p>
                <input
                  className={styles.file}
                  id="evidence-file"
                  name="evidence-file"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleFile}
                  aria-describedby="evidence-file-hint"
                />
              </div>
              {fileError !== null && (
                <p className={styles.error} role="alert">
                  {fileError}
                </p>
              )}
              {previewUrl !== null && file !== null && (
                <EvidencePreview src={previewUrl} filename={file.name} />
              )}
              {classify.isPending && (
                <p className={styles.pending}>Checking the screenshot. Pixels stay in this tab.</p>
              )}
              {classify.isError && (
                <p className={styles.error} role="alert">
                  {errorMessage(classify.error)} The draft can still be prepared without a
                  classification.
                </p>
              )}
              {classify.isSuccess && <EvidenceClassification result={classify.data} />}
            </div>
          )}
        </fieldset>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="report-platform">
            Report platform
          </label>
          <select
            className={styles.control}
            id="report-platform"
            name="report-platform"
            required
            value={platform}
            onChange={handlePlatform}
          >
            <option value="">Choose a platform</option>
            {REPORT_PLATFORM_OPTIONS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          <PlatformReportPaths platform={platform} />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="content-url">
            Content URL (optional)
          </label>
          <input
            className={styles.control}
            id="content-url"
            name="content-url"
            type="url"
            inputMode="url"
            value={contentUrl}
            onChange={handleUrl}
            aria-describedby="content-url-hint"
            aria-invalid={urlError !== null}
          />
          <p className={styles.hint} id="content-url-hint">
            Typed by you. Amanah does not fetch it.
          </p>
          {urlError !== null && (
            <p className={styles.error} role="alert">
              {urlError}
            </p>
          )}
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="reporter-note">
            What you saw (optional)
          </label>
          <textarea
            className={styles.note}
            id="reporter-note"
            name="reporter-note"
            rows={4}
            maxLength={2000}
            value={note}
            onChange={handleNote}
            aria-describedby="reporter-note-hint"
          />
          <p className={styles.hint} id="reporter-note-hint">
            Your wording goes into the draft as you wrote it.
          </p>
        </div>

        <p className={styles.brigade}>
          Prepare one report for content you saw. Do not organise mass duplicate reports.
        </p>

        <button type="submit" className={styles.primaryAction} disabled={prepare.isPending}>
          Generate draft
        </button>
        {prepare.isPending && <p className={styles.pending}>Preparing the draft.</p>}
        {prepare.isError && (
          <p className={styles.error} role="alert">
            {errorMessage(prepare.error)} You can change the details and try again.
          </p>
        )}
      </form>

      {prepare.isSuccess && <ReportDraftPreview draft={prepare.data} />}
    </section>
  );
}
