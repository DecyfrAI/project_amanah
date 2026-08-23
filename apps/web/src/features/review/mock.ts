/**
 * Local constants behind the Review queue mockup.
 *
 * Every value here was written by hand to show the layout. Excerpts are
 * synthetic othering remarks shown in full, never real slurs, and no container,
 * account, or channel names a real one.
 *
 * When the backend exists this file is deleted, not adapted: the queue will come
 * from `GET /v1/review/tasks` through `src/api/`, so no component may learn the
 * shape of these constants.
 */

/** Why a person, rather than the pipeline, has to look at this item. */
export type QueueReason = 'low_confidence' | 'model_disagreement' | 'spike_membership' | 'novelty';

export interface QueueItem {
  /** Opaque item reference. Never a source URL, handle, or sequential number. */
  readonly id: string;
  readonly platform: string;
  /** Synthetic container title: the video or thread the item sits in. */
  readonly container: string;
  readonly observedAt: string;
  /** The stance the model proposes, in reader-facing words. */
  readonly proposedLabel: string;
  /** Model score on its own scale, not a proportion of anything. */
  readonly modelScore: number;
  readonly confidenceTier: 'High' | 'Medium' | 'Low';
  /** Taxonomy severity, 0 to 3, as proposed by the model and not yet reviewed. */
  readonly severityBand: 0 | 1 | 2 | 3;
  readonly severityLabel: string;
  readonly reason: QueueReason;
  /** Synthetic othering remark, shown in full. Never a real slur. */
  readonly excerpt: string;
  readonly modelVersion: string;
}

export const QUEUE_REASON_LABELS: Record<QueueReason, string> = {
  low_confidence: 'Low model confidence',
  model_disagreement: 'Two model runs disagreed',
  spike_membership: 'Belongs to a day that coincides with a volume spike',
  novelty: 'Wording unlike anything in the evaluation set',
};

export const QUEUE_ITEMS: readonly QueueItem[] = [
  {
    id: 'itm_7fb2c9',
    platform: 'YouTube',
    container: 'Council approves mosque extension, public gallery recording',
    observedAt: '2026-08-21T09:12:00+00:00',
    proposedLabel: 'Classified as likely anti-Muslim hate',
    modelScore: 0.58,
    confidenceTier: 'Low',
    severityBand: 2,
    severityLabel: 'Derogation',
    reason: 'low_confidence',
    excerpt:
      "They don't belong here. There are other places they can go. That building should never have been allowed.",
    modelVersion: 'gemini-classifier 0.4.2, taxonomy v3',
  },
  {
    id: 'itm_3ad014',
    platform: 'Reddit',
    container: 'Thread: new prayer room in the university library',
    observedAt: '2026-08-21T14:48:00+00:00',
    proposedLabel: 'Classified as counterspeech or quotation',
    modelScore: 0.44,
    confidenceTier: 'Low',
    severityBand: 0,
    severityLabel: 'No severity proposed',
    reason: 'model_disagreement',
    excerpt:
      'Quoting an earlier remark: they do not belong here. I am arguing against that, not repeating it as my view.',
    modelVersion: 'gemini-classifier 0.4.2, taxonomy v3',
  },
  {
    id: 'itm_91c8de',
    platform: 'Bluesky',
    container: 'Post replying to a national headline about a planning decision',
    observedAt: '2026-08-22T07:05:00+00:00',
    proposedLabel: 'Classified as likely anti-Muslim hate',
    modelScore: 0.91,
    confidenceTier: 'High',
    severityBand: 3,
    severityLabel: 'Threat or incitement',
    reason: 'spike_membership',
    excerpt: 'Someone should make them leave before the vote.',
    modelVersion: 'gemini-classifier 0.4.2, taxonomy v3',
  },
  {
    id: 'itm_5e40ba',
    platform: 'YouTube',
    container: 'Explainer clip: what the new planning rules change',
    observedAt: '2026-08-22T11:26:00+00:00',
    proposedLabel: 'Classified as non-hateful discussion',
    modelScore: 0.52,
    confidenceTier: 'Low',
    severityBand: 0,
    severityLabel: 'No severity proposed',
    reason: 'novelty',
    excerpt: 'They are not like us, and the way they talk about this neighbourhood says it all.',
    modelVersion: 'gemini-classifier 0.4.2, taxonomy v3',
  },
  {
    id: 'itm_2c7715',
    platform: 'Open datapack (source shown as N/A)',
    container: 'Imported row, dataset annotation says "hateful"',
    observedAt: '2026-08-19T00:00:00+00:00',
    proposedLabel: 'Classified as likely anti-Muslim hate',
    modelScore: 0.77,
    confidenceTier: 'Medium',
    severityBand: 2,
    severityLabel: 'Collective blame',
    reason: 'model_disagreement',
    excerpt: 'They are all the same. That crime is on the whole community.',
    modelVersion: 'gemini-classifier 0.4.2, taxonomy v3',
  },
  {
    id: 'itm_a80f36',
    platform: 'Mastodon (single instance)',
    container: 'Thread: local coverage of a vandalism report',
    observedAt: '2026-08-22T16:39:00+00:00',
    proposedLabel: 'Classified as likely anti-Muslim hate',
    modelScore: 0.63,
    confidenceTier: 'Medium',
    severityBand: 1,
    severityLabel: 'Animosity',
    reason: 'spike_membership',
    excerpt: 'Those people are not to be believed.',
    modelVersion: 'gemini-classifier 0.4.2, taxonomy v3',
  },
];

export interface QueueFigure {
  readonly id: string;
  readonly label: string;
  readonly value: string;
  /** The count and the population it came out of. Never a bare proportion. */
  readonly basis: string;
  readonly definition: string;
}

export const QUEUE_FIGURES: readonly QueueFigure[] = [
  {
    id: 'awaiting',
    label: 'Items awaiting review',
    value: '34',
    basis: '34 of 1,208 classified items in the window',
    definition:
      'Classified items the pipeline routed to a person, out of everything it classified between 9 and 22 August 2026.',
  },
  {
    id: 'median-decision',
    label: 'Median time to decision',
    value: '4 h 12 min',
    basis: 'Median of 57 decisions recorded in the window',
    definition:
      'Time between an item entering the queue and a reviewer appending a decision. A median, so a single slow item does not move it.',
  },
  {
    id: 'agreement',
    label: 'Reviewers agreed with the model',
    value: '41 of 57 (72%)',
    basis: '41 confirmations of 57 decided items',
    definition:
      'Decisions that confirmed the proposed label rather than correcting it. Agreement is not accuracy: both a reviewer and the model can be wrong.',
  },
];
