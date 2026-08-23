/** Five on-theme categorical marks. Colour repeats the label, never replaces it. */
export const CHART_TONE_COUNT = 5;

export function chartTone(index: number): 1 | 2 | 3 | 4 | 5 {
  const slot = (index % CHART_TONE_COUNT) + 1;
  if (slot === 1 || slot === 2 || slot === 3 || slot === 4 || slot === 5) {
    return slot;
  }
  return 1;
}
