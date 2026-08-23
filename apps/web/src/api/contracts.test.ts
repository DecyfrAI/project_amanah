import { describe, expect, it } from 'vitest';

import {
  DiscussionCatalogSchema,
  EvidenceClassifyRequestSchema,
  InsightListSchema,
  NewsItemSchema,
  ReportDraftRequestSchema,
} from './contracts';

import discussionsJson from '@/fixtures/discussions.json' with { type: 'json' };
import insightsJson from '@/fixtures/insights.json' with { type: 'json' };
import newsJson from '@/fixtures/news.json' with { type: 'json' };

describe('fixture contracts', () => {
  it('accepts the committed insights fixture', () => {
    const parsed = InsightListSchema.parse(insightsJson);
    const first = parsed.insights[0];
    expect(first).toBeDefined();
    expect(first?.facts[0]?.denominator).toBe(312);
    expect(first?.facts[0]?.numerator).toBe(74);
  });

  it('accepts the committed discussion fixture', () => {
    const parsed = DiscussionCatalogSchema.parse(discussionsJson);
    const thread = parsed.threads[0];
    expect(thread?.posts[0]?.capture?.filterHash).toContain('collective_blame');
    expect(thread?.posts[0]?.author.displayName).toBe('Amina R.');
  });

  it('accepts the committed news fixture as public-safe context items', () => {
    const items = NewsItemSchema.array().parse(newsJson.items);
    const commons = items.find((item) => item.id === 'news_bbc_0815');

    expect(items).toHaveLength(12);
    expect(commons?.title).toMatch(/mosque safety/i);
    expect(commons?.url).toMatch(/^https:\/\//);
    for (const item of items) {
      expect(item).not.toHaveProperty('classification');
      expect(item).not.toHaveProperty('hateType');
      expect(item.summary).not.toMatch(/nigger|kike|paki|raghead/i);
    }
  });
});

describe('ReportDraftRequestSchema', () => {
  it('accepts filename and size without an image payload', () => {
    const parsed = ReportDraftRequestSchema.parse({
      platform: 'reddit',
      has_image: true,
      image_filename: 'capture.png',
      image_byte_size: 2048,
    });

    expect(parsed).not.toHaveProperty('image_src');
    expect(parsed).not.toHaveProperty('image_data');
  });

  it('rejects a content URL that is not http or https', () => {
    expect(() =>
      ReportDraftRequestSchema.parse({
        platform: 'youtube',
        has_image: false,
        content_url: 'javascript:alert(1)',
      }),
    ).toThrow();
  });
});

describe('EvidenceClassifyRequestSchema', () => {
  it('accepts filename and size without pixels', () => {
    const parsed = EvidenceClassifyRequestSchema.parse({
      image_filename: 'capture.png',
      image_byte_size: 2048,
    });

    expect(parsed).not.toHaveProperty('image_src');
    expect(parsed).not.toHaveProperty('image_data');
    expect(parsed).not.toHaveProperty('image');
  });
});
