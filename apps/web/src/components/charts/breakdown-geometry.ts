/**
 * Geometry for the composition figures.
 *
 * Kept out of the views so a slice, stem, or bubble can be checked without
 * rendering, and so SVG attributes stay numbers rather than guessed CSS.
 */

export interface DonutSlice {
  readonly key: string;
  readonly length: number;
  readonly offset: number;
}

export function donutSlices(
  rows: readonly { key: string; count: number }[],
  total: number,
  circumference: number,
): readonly DonutSlice[] {
  let cursor = 0;

  return rows.map((row) => {
    const length = total === 0 ? 0 : (row.count / total) * circumference;
    const slice = { key: row.key, length, offset: cursor };
    cursor += length;
    return slice;
  });
}

/** Area scales with count, so a twice-as-large share is a twice-as-large disc. */
export function bubbleDiameter(
  count: number,
  largest: number,
  minPx: number,
  maxPx: number,
): number {
  if (largest <= 0 || count <= 0) {
    return minPx;
  }
  const scale = Math.sqrt(count / largest);
  return minPx + (maxPx - minPx) * scale;
}
