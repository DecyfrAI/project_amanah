/**
 * Screenshot chosen for a platform-report draft.
 *
 * The file is validated in the tab and previewed from an object URL. It is
 * never written to disk or sent to the API: only filename and size travel with
 * the draft request.
 */
export const EVIDENCE_MAX_BYTES = 5 * 1024 * 1024;

const ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);

export function validateEvidenceFile(file: File): File {
  if (!ALLOWED_TYPES.has(file.type)) {
    throw new Error('Choose a PNG, JPEG or WebP screenshot.');
  }

  if (file.size > EVIDENCE_MAX_BYTES) {
    throw new Error(
      `That image is ${Math.round(file.size / 1024)} KB. Choose one under ${Math.round(
        EVIDENCE_MAX_BYTES / 1024,
      )} KB.`,
    );
  }

  return file;
}
