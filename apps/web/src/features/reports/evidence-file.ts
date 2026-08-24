/**
 * Screenshot chosen for a platform-report draft.
 *
 * The file is checked in the tab before upload and previewed from an object URL.
 * This is a convenience check only; the backend re-validates and cleans the
 * bytes before private storage.
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
