/**
 * Reader-facing wording for the taxonomy enums.
 *
 * The wire values are stable identifiers; these are what a reviewer reads. Kept
 * in one place so a label cannot drift between the queue row, the decision
 * history, and the correction form.
 */
import type { HateType, ReviewTaskType, Stance } from '@/api';

export const STANCE_LABELS: Record<Stance, string> = {
  likely_anti_muslim: 'Classified as likely anti-Muslim hate',
  non_hateful_discussion: 'Classified as non-hateful discussion',
  counterspeech_or_quotation: 'Classified as counterspeech or quotation',
  uncertain: 'Stance uncertain',
};

export const HATE_TYPE_LABELS: Record<HateType, string> = {
  animosity: 'Animosity',
  derogation: 'Derogation',
  dehumanization: 'Dehumanization',
  exclusion: 'Exclusion',
  threat_or_incitement: 'Threat or incitement',
  collective_blame: 'Collective blame',
  other: 'Other',
};

/** Severity 0 means no anti-Muslim harm was identified, not "mild harm". */
export const SEVERITY_LABELS: Record<number, string> = {
  0: 'no severity proposed',
  1: 'low',
  2: 'moderate',
  3: 'high',
};

export const TASK_TYPE_LABELS: Record<ReviewTaskType, string> = {
  dispute: 'A user disputed this classification',
  low_confidence: 'Low model confidence',
  severity_escalation: 'Proposed severity always needs a person',
  model_disagreement: 'Two model runs disagreed',
  uncertain_relevance: 'Relevance to Muslims or Islam is uncertain',
  invalid_output: 'The model returned output the schema refused',
};

export const PLATFORM_LABELS: Record<string, string> = {
  youtube: 'YouTube',
  reddit: 'Reddit',
  bluesky: 'Bluesky',
  news_web: 'News web',
  user_submitted: 'User submitted',
  not_applicable: 'Open datapack (source shown as N/A)',
};
