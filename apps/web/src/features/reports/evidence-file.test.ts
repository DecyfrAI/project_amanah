import { describe, expect, it } from 'vitest';

import { EVIDENCE_MAX_BYTES, validateEvidenceFile } from './evidence-file';

function fileOfSize(bytes: number, type: string, name = 'capture.png'): File {
  return new File([new Uint8Array(bytes)], name, { type });
}

describe('validateEvidenceFile', () => {
  it('refuses a file that is not an accepted image type', () => {
    expect(() => validateEvidenceFile(fileOfSize(10, 'application/pdf', 'notes.pdf'))).toThrow(
      /PNG, JPEG or WebP/i,
    );
  });

  it('refuses an image past the size limit, and says how large it was', () => {
    expect(() => validateEvidenceFile(fileOfSize(EVIDENCE_MAX_BYTES + 2048, 'image/png'))).toThrow(
      /Choose one under 5120 KB/i,
    );
  });

  it('returns an accepted image so the tab can preview it in memory', () => {
    const file = fileOfSize(64, 'image/jpeg', 'shot.jpg');
    expect(validateEvidenceFile(file)).toBe(file);
  });
});
