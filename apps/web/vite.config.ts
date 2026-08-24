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
  build: {
    rollupOptions: {
      output: {
        /*
         * Keep the entry chunk under Vite's 500 kB warning (F-S21.6). The
         * heavyweights are stable third-party code that caches well on its
         * own: React and the router, TanStack Query, Zod, and the Supabase
         * client. Route-level views are already lazy.
         */
        manualChunks(id: string): string | undefined {
          if (!id.includes('node_modules')) {
            return undefined;
          }
          if (/[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/.test(id)) {
            return 'react';
          }
          if (id.includes('@tanstack')) {
            return 'query';
          }
          if (/[\\/]zod[\\/]/.test(id)) {
            return 'zod';
          }
          if (id.includes('@supabase')) {
            return 'supabase';
          }
          return undefined;
        },
      },
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
