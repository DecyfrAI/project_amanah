/**
 * Plain-language rendering of a classification.
 *
 * The reviewer-facing card states the taxonomy fields as they are, which is
 * right for someone who works with them daily. This is for the other reader:
 * someone trying the model to see what it does. Same values, ordinary sentences,
 * and the caveats kept at full weight rather than softened for readability.
 */
import type { HateType, ImageClassification, Relevance, Stance } from '@/api';

export function stanceSentence(stance: Stance): string {
  const sentences: Record<Stance, string> = {
    likely_anti_muslim: 'The model thinks this is likely anti-Muslim hate.',
    non_hateful_discussion: 'The model thinks this is discussion about Muslims or Islam, not hate.',
    counterspeech_or_quotation:
      'The model thinks this is someone arguing against hate, or quoting it, rather than expressing it.',
    uncertain: 'The model could not settle on what this is.',
  };
  return sentences[stance];
}

export function relevanceSentence(relevance: Relevance): string {
  const sentences: Record<Relevance, string> = {
    muslim_related: 'It read this as being about Muslims or Islam.',
    not_related: 'It did not read this as being about Muslims or Islam.',
    uncertain: 'It was not sure whether this is about Muslims or Islam.',
  };
  return sentences[relevance];
}

export function confidenceSentence(tier: ImageClassification['confidence_tier']): string {
  const sentences: Record<ImageClassification['confidence_tier'], string> = {
    low: 'It is not confident. A score this low is exactly why an item goes to a person.',
    medium: 'It is moderately confident. That is not the same as being right.',
    high: 'It is confident, as the model measures confidence. That is still not proof.',
  };
  return sentences[tier];
}

/** Severity 0 means no harm was identified, not "a little harm". */
export function severitySentence(severity: number | null): string {
  if (severity === null || severity === 0) {
    return 'It did not propose a harm level.';
  }
  const sentences: Record<number, string> = {
    1: 'It put this at the lowest harm level the taxonomy has.',
    2: 'It put this at a moderate harm level.',
    3: 'It put this at the highest harm level. An item here always goes to a person.',
  };
  return sentences[severity] ?? 'It did not propose a harm level.';
}

/** What each taxonomy term means, for a reader who has not read the taxonomy. */
export const HATE_TYPE_PLAIN: Record<HateType, string> = {
  animosity: 'hostility towards Muslims',
  derogation: 'talking down about Muslims',
  dehumanization: 'describing Muslims as less than human',
  exclusion: 'saying Muslims do not belong',
  threat_or_incitement: 'threatening harm, or urging others to',
  collective_blame: 'blaming all Muslims for one act',
  other: 'something the taxonomy does not name',
};
