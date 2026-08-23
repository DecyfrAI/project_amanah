/**
 * Small enough to sit in `sessionStorage` without risking a quota failure, and
 * large enough for any reasonable profile picture.
 */
export const AVATAR_MAX_BYTES = 256 * 1024;

const ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);

/**
 * Reads a chosen image as a data URL.
 *
 * The type and size are checked before reading rather than after, so an
 * oversized file is refused with a clear message instead of filling storage and
 * failing on write. The picture never leaves the browser.
 */
export async function readImageFile(file: File): Promise<string> {
  if (!ALLOWED_TYPES.has(file.type)) {
    throw new Error('Choose a PNG, JPEG or WebP image.');
  }

  if (file.size > AVATAR_MAX_BYTES) {
    throw new Error(
      `That image is ${Math.round(file.size / 1024)} KB. Choose one under ${Math.round(
        AVATAR_MAX_BYTES / 1024,
      )} KB.`,
    );
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener('load', () => {
      const result = reader.result;
      if (typeof result === 'string') {
        resolve(result);
        return;
      }
      reject(new Error('That picture could not be read. Try another.'));
    });
    reader.addEventListener('error', () => {
      reject(new Error('That picture could not be read. Try another.'));
    });
    reader.readAsDataURL(file);
  });
}
