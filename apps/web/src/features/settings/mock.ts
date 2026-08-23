/**
 * Local constants behind the Settings mockup.
 *
 * The sample rows exist so a reader can see what a density choice does to a
 * table. They are written by hand and carry no excerpt at all, since a settings
 * page is the last place harmful wording should appear unasked.
 */

export type TableDensity = 'comfortable' | 'compact';

export interface DensityOption {
  readonly value: TableDensity;
  readonly label: string;
  readonly detail: string;
}

export const DENSITY_OPTIONS: readonly DensityOption[] = [
  {
    value: 'comfortable',
    label: 'Comfortable',
    detail: 'Taller rows, easier to scan for a long review session.',
  },
  {
    value: 'compact',
    label: 'Compact',
    detail: 'Shorter rows, more of the table on screen at once.',
  },
];

export interface SampleRow {
  readonly id: string;
  readonly platform: string;
  readonly proposedLabel: string;
  readonly modelScore: number;
}

export const SAMPLE_ROWS: readonly SampleRow[] = [
  {
    id: 'itm_7fb2c9',
    platform: 'YouTube',
    proposedLabel: 'Classified as likely anti-Muslim hate',
    modelScore: 0.58,
  },
  {
    id: 'itm_3ad014',
    platform: 'Reddit',
    proposedLabel: 'Classified as counterspeech or quotation',
    modelScore: 0.44,
  },
  {
    id: 'itm_91c8de',
    platform: 'Bluesky',
    proposedLabel: 'Classified as likely anti-Muslim hate',
    modelScore: 0.91,
  },
];
