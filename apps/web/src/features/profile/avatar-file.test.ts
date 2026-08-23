import { describe, expect, it } from 'vitest';

import { AVATAR_MAX_BYTES, readImageFile } from './avatar-file';

function fileOfSize(bytes: number, type: string): File {
  return new File([new Uint8Array(bytes)], 'picture', { type });
}

describe('readImageFile', () => {
  it('refuses a file that is not an accepted image type', async () => {
    await expect(readImageFile(fileOfSize(10, 'application/pdf'))).rejects.toThrow(
      /PNG, JPEG or WebP/i,
    );
  });

  it('refuses an image past the storage limit, and says how large it was', async () => {
    await expect(readImageFile(fileOfSize(AVATAR_MAX_BYTES + 1024, 'image/png'))).rejects.toThrow(
      /Choose one under 256 KB/i,
    );
  });

  it('reads an accepted image as a data URL', async () => {
    const dataUrl = await readImageFile(fileOfSize(64, 'image/png'));

    expect(dataUrl.startsWith('data:image/png;base64,')).toBe(true);
  });
});
