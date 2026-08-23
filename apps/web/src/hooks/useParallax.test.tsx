import { render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useParallax } from './useParallax';

function mockMatchMedia(matches: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

function Harness({ speed }: { speed: number }) {
  const layerRef = useParallax<HTMLDivElement>(speed);
  return (
    <div data-testid="parent">
      <div ref={layerRef} data-testid="layer" />
    </div>
  );
}

function stubParentGeometry(parent: HTMLElement, rect: { top: number; height: number }): void {
  vi.spyOn(parent, 'getBoundingClientRect').mockReturnValue({
    top: rect.top,
    height: rect.height,
    width: 320,
    left: 0,
    right: 320,
    bottom: rect.top + rect.height,
    x: 0,
    y: rect.top,
    toJSON: () => '',
  });
  Object.defineProperty(parent, 'clientHeight', { configurable: true, value: rect.height });
}

describe('useParallax', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(800);
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
    vi.stubGlobal('cancelAnimationFrame', () => undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('offsets from the parent position in the viewport, not document scroll', () => {
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 2400 });

    const { getByTestId } = render(<Harness speed={0.2} />);
    const parent = getByTestId('parent');
    stubParentGeometry(parent, { top: 400, height: 500 });

    window.dispatchEvent(new Event('scroll'));

    // Displacement from viewport centre: 400 + 250 - 400 = 250.
    // Travel: -250 * 0.2 = -50. Limit is 100, so the raw value stands.
    expect(getByTestId('layer').style.getPropertyValue('--parallax-offset')).toBe('-50px');
  });

  it('clamps travel so a distant section cannot leave its frame', () => {
    const { getByTestId } = render(<Harness speed={0.4} />);
    const parent = getByTestId('parent');
    stubParentGeometry(parent, { top: 4000, height: 500 });

    window.dispatchEvent(new Event('scroll'));

    expect(getByTestId('layer').style.getPropertyValue('--parallax-offset')).toBe('-100px');
  });

  it('does not write an offset when the reader prefers reduced motion', () => {
    mockMatchMedia(true);

    const { getByTestId } = render(<Harness speed={0.2} />);

    expect(getByTestId('layer').style.getPropertyValue('--parallax-offset')).toBe('');
  });
});
