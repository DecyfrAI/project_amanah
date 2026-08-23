import { describe, expect, it } from 'vitest';

import { articleLinkLabel, formatNewsPublishedAt, outboundCue } from './news-copy';

describe('news-copy', () => {
  it('names the outbound article without calling it a classification', () => {
    const label = articleLinkLabel(
      'Commons hears questions on mosque safety after vandalism in a northern city',
      'BBC News',
    );

    expect(label).toBe(
      'Commons hears questions on mosque safety after vandalism in a northern city (opens article on BBC News)',
    );
    expect(label).not.toMatch(/classified|likely hate|hate speech/i);
    expect(outboundCue('BBC News')).toBe('Opens article on BBC News');
  });

  it('states an absolute UTC date and a relative phrase', () => {
    const formatted = formatNewsPublishedAt(
      '2026-08-15T10:28:00+00:00',
      new Date('2026-08-23T12:00:00+00:00'),
    );

    expect(formatted.absolute).toBe('15 Aug 2026');
    expect(formatted.relative).toBe('8 days ago');
    expect(`${formatted.absolute} ${formatted.relative}`).not.toMatch(/—/);
  });
});
