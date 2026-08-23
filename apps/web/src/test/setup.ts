import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/*
 * Node 22+ can leave `localStorage` undefined unless a file-backed store is
 * configured. The workspace chrome and tour persist to it, so tests need a
 * memory-backed shim rather than throwing on every preference read.
 */
const localStore = new Map<string, string>();
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  writable: true,
  value: {
    get length(): number {
      return localStore.size;
    },
    clear(): void {
      localStore.clear();
    },
    getItem(key: string): string | null {
      return localStore.has(key) ? (localStore.get(key) ?? null) : null;
    },
    key(index: number): string | null {
      return [...localStore.keys()][index] ?? null;
    },
    removeItem(key: string): void {
      localStore.delete(key);
    },
    setItem(key: string, value: string): void {
      localStore.set(key, String(value));
    },
  },
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }),
});

function ImmediateIntersectionObserver(callback: IntersectionObserverCallback) {
  const observer: IntersectionObserver = {
    root: null,
    rootMargin: '0px',
    scrollMargin: '0px',
    thresholds: [0],
    observe(target: Element): void {
      callback([{ isIntersecting: true, target } as IntersectionObserverEntry], observer);
    },
    unobserve(): void {},
    disconnect(): void {},
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    },
  };
  return observer;
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: ImmediateIntersectionObserver,
});

function polyfillShowModal(this: HTMLDialogElement): void {
  this.setAttribute('open', '');
}

function polyfillClose(this: HTMLDialogElement): void {
  this.removeAttribute('open');
  this.dispatchEvent(new Event('close'));
}

/*
 * jsdom's <dialog> does not implement showModal. The workspace uses native
 * dialogs for focus trapping, so tests need the open attribute to be set the
 * same way a browser would.
 */
if (typeof HTMLDialogElement !== 'undefined') {
  HTMLDialogElement.prototype.show = polyfillShowModal;
  HTMLDialogElement.prototype.showModal = polyfillShowModal;
  HTMLDialogElement.prototype.close = polyfillClose;
}

// Testing Library does not auto-clean when `globals` is enabled in some setups.
// Explicit teardown keeps every test independent, per rules/testing.md.
afterEach(() => {
  cleanup();
});
