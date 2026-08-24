import { useMutation } from '@tanstack/react-query';

import { apiClient, type ImageUpload } from '@/api';

/**
 * Sends one image to the backend, which cleans and stores it (B-S28).
 *
 * Upload and classification are separate calls on purpose: a model failure must
 * not cost the person their file. The result carries an identifier they can
 * classify afterwards, and a short-lived signed URL for the preview.
 */
export function useUploadImage() {
  return useMutation({
    mutationFn: (file: File): Promise<ImageUpload> => apiClient.uploadImage(file),
  });
}
