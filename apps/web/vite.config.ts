/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const DEFAULT_DEV_PORT = 5173;
const WATCH_POLL_INTERVAL_MS = 250;

export default defineConfig({
  plugins: [react()],
  server: {
    // Honour an externally assigned port so the dev server can coexist with
    // whatever else is already bound to the default.
    port: Number(process.env.PORT) || DEFAULT_DEV_PORT,

    /*
     * Fail loudly instead of drifting onto a neighbouring port. Several other
     * projects on this machine bind 5173 upward, and a silent hop meant the
     * browser could load a different application from the URL we printed.
     */
    strictPort: true,

    /*
     * Poll for changes. Filesystem events do not reach the watcher reliably on
     * this workspace, and a watcher that misses an edit is worse than a slow
     * one: the server keeps serving its first transform of every module, so
     * edits appear to have no effect at all.
     */
    watch: {
      usePolling: true,
      interval: WATCH_POLL_INTERVAL_MS,
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['src/test/**', '**/*.d.ts', '**/*.config.*'],
    },
  },
});
