import { describe, expect, it } from 'vitest';

import { ReportDraftSchema } from '@/api/contracts';

import { FIXTURE_QUOTE, prepareReportDraft, reportPlatformFromLabel } from './prepare-report-draft';

describe('prepareReportDraft', () => {
  it('fills a YouTube placeholder addressee and says the draft was not sent', () => {
    const draft = ReportDraftSchema.parse(
      prepareReportDraft({
        platform: 'youtube',
        has_image: false,
      }),
    );

    expect(draft.to).toBe('report@youtube.example');
    expect(draft.subject).toMatch(/YouTube/);
    expect(draft.body).toMatch(/has not sent it/i);
    expect(draft.body).toMatch(/not a confirmed finding/i);
    expect(draft.body).toMatch(/does not notify a government authority/i);
    expect(draft.status).toBe('prepared_not_sent');
    expect(draft.to_kind).toBe('placeholder');
  });

  it('uses a Reddit addressee and subject when that platform is selected', () => {
    const draft = prepareReportDraft({ platform: 'reddit', has_image: false });

    expect(draft.to).toBe('report@reddit.example');
    expect(draft.to_kind).toBe('placeholder');
    expect(draft.official_report_url).toBe('https://www.reddit.com/report');
    expect(draft.subject).toMatch(/Reddit/);
    expect(draft.body).toMatch(/official Reddit report form/i);
  });

  it('points YouTube drafts at the official reporting help page, not a live inbox', () => {
    const draft = prepareReportDraft({ platform: 'youtube', has_image: false });

    expect(draft.official_report_url).toBe('https://support.google.com/youtube/answer/2802027');
    expect(draft.to_note).toMatch(/does not publish a public mailbox/i);
  });

  it('quotes the reporter note in full rather than replacing it with a redaction marker', () => {
    const note = "They don't belong here. Bloody go somewhere else.";
    const draft = prepareReportDraft({
      platform: 'youtube',
      has_image: false,
      reporter_note: note,
    });

    expect(draft.likely_quote).toBe(note);
    expect(draft.body).toContain(note);
    expect(draft.body).not.toMatch(/\[Redacted/i);
  });

  it('uses the milder fixture line in full when no note is typed', () => {
    const draft = prepareReportDraft({
      platform: 'other',
      has_image: true,
      image_filename: 'capture.png',
      image_byte_size: 2048,
    });

    expect(draft.likely_quote).toBe(FIXTURE_QUOTE);
    expect(draft.body).toContain(FIXTURE_QUOTE);
    expect(draft.body).toContain('capture.png');
    expect(draft.body).not.toMatch(/\[Redacted/i);
  });

  it('records a content URL as typed and does not treat it as a fetch', () => {
    const draft = prepareReportDraft({
      platform: 'reddit',
      has_image: false,
      content_url: 'https://www.reddit.com/r/example/comments/abc123/thread/',
    });

    expect(draft.body).toContain('https://www.reddit.com/r/example/comments/abc123/thread/');
    expect(draft.body).toMatch(/not fetched/i);
  });
});

describe('reportPlatformFromLabel', () => {
  it('maps review labels onto the report catalog', () => {
    expect(reportPlatformFromLabel('YouTube')).toBe('youtube');
    expect(reportPlatformFromLabel('Reddit')).toBe('reddit');
    expect(reportPlatformFromLabel('Bluesky')).toBe('other');
  });
});
