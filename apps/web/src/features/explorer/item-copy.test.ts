import { describe, expect, it } from 'vitest';

import { classificationLabel, itemSeverityLabel, itemTypeLabel } from './item-copy';

describe('item-copy', () => {
  it('keeps the likely-hate wording as a classification, not a finding', () => {
    expect(classificationLabel('likely_hate')).toBe('Classified as likely anti-Muslim hate');
    expect(classificationLabel('not_hate')).toBe('Not classified as hate');
  });

  it('does not invent a type or a severity when none was recorded', () => {
    expect(itemTypeLabel(null)).toBe('Not applicable');
    expect(itemSeverityLabel(null)).toBe('No severity recorded');
    expect(itemSeverityLabel(2)).toBe('Severity 2, moderate');
  });
});
