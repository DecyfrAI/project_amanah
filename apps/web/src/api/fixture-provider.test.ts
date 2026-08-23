import { beforeEach, describe, expect, it } from 'vitest';

import { fixtureProvider, resetFixtureProvider } from './fixture-provider';

describe('fixtureProvider overview', () => {
  it('keeps the fixture arithmetic self-consistent', async () => {
    const overview = await fixtureProvider.getOverview({});

    const collected = overview.daily.filter((day) => day.collected);
    const relevant = collected.reduce((total, day) => total + (day.relevant ?? 0), 0);
    const likelyHate = collected.reduce((total, day) => total + (day.likelyHate ?? 0), 0);
    const nonRelevant = collected.reduce((total, day) => total + (day.nonRelevant ?? 0), 0);

    expect(relevant).toBe(overview.coverage.itemsRelevant);
    expect(relevant + nonRelevant).toBe(overview.coverage.itemsObserved);

    const rate = overview.metrics.find((metric) => metric.id === 'rate');
    expect(rate?.numerator).toBe(likelyHate);
    expect(rate?.denominator).toBe(relevant);
  });

  it('reports a failed collection day as uncollected with null counts, never as zero', async () => {
    const overview = await fixtureProvider.getOverview({});
    const gap = overview.daily.find((day) => !day.collected);

    expect(gap?.date).toBe('2026-08-07');
    expect(gap?.relevant).toBeNull();
    expect(gap?.likelyHate).toBeNull();
    expect(gap?.observed).toBeNull();
    expect(overview.coverage.warnings).not.toHaveLength(0);
  });

  it('marks every model-derived metric as model-only', async () => {
    const overview = await fixtureProvider.getOverview({});

    const modelOnly = overview.metrics.filter((metric) => metric.isModelOnly).map((m) => m.id);
    expect(modelOnly).toContain('likely-hate');
    expect(modelOnly).toContain('rate');
    expect(modelOnly).not.toContain('reviewed');
    expect(modelOnly).not.toContain('pending');
  });

  it('states a denominator for every rate', async () => {
    const overview = await fixtureProvider.getOverview({});

    for (const metric of overview.metrics.filter((entry) => entry.unit === 'rate')) {
      expect(metric.numerator).not.toBeNull();
      expect(metric.denominator).not.toBeNull();
    }
  });

  it('narrows both the window and the source when asked', async () => {
    const overview = await fixtureProvider.getOverview({
      from: '2026-08-01',
      to: '2026-08-16',
      platforms: ['youtube'],
    });

    expect(overview.applied.from).toBe('2026-08-01');
    expect(overview.applied.to).toBe('2026-08-16');
    expect(overview.applied.platforms).toEqual(['youtube']);
    expect(overview.coverage.sources).toEqual(['youtube']);
    expect(overview.coverage.itemsObserved).toBe(1798);
    expect(overview.coverage.itemsRelevant).toBe(390);

    const hate = overview.metrics.find((metric) => metric.id === 'likely-hate');
    expect(hate?.value).toBe(87);
  });

  it('keeps type shares adding to the likely-hate total', async () => {
    const overview = await fixtureProvider.getOverview({});
    const byType = overview.breakdowns.find((entry) => entry.id === 'by-type');
    const hate = overview.metrics.find((metric) => metric.id === 'likely-hate');

    expect(byType?.rows.reduce((sum, row) => sum + row.count, 0)).toBe(hate?.value);
  });
});

describe('fixtureProvider items', () => {
  it('returns only the examples that match the filters', async () => {
    const page = await fixtureProvider.searchItems({
      from: '2026-06-18',
      to: '2026-08-16',
      hateTypes: ['threat'],
    });

    expect(page.matched).toBe(1);
    expect(page.items[0]?.id).toBe('itm_9b52');
    expect(page.items[0]?.hateType).toBe('threat');
  });

  it('filters explorer rows by a keyword query', async () => {
    const page = await fixtureProvider.searchItems({ q: 'poster' });

    expect(page.items.some((item) => item.id === 'itm_img_01')).toBe(true);
    expect(
      page.items.every(
        (item) =>
          item.id === 'itm_img_01' ||
          item.redactedExcerpt.toLowerCase().includes('poster') ||
          item.image?.formNote.toLowerCase().includes('poster'),
      ),
    ).toBe(true);
  });

  it('never exposes an author or an unredacted slur', async () => {
    const page = await fixtureProvider.searchItems({});

    expect(page.matched).toBeGreaterThan(0);
    for (const item of page.items) {
      expect(item).not.toHaveProperty('author');
      expect(item.redactedExcerpt).not.toMatch(/nigger|kike|paki|raghead/i);
      expect(item.redactedExcerpt).not.toMatch(/\[.*redacted\]/i);
    }
  });
});

describe('fixtureProvider snapshots', () => {
  beforeEach(() => {
    resetFixtureProvider();
  });

  it('creates a snapshot with the figure counts and an empty thread', async () => {
    const insight = await fixtureProvider.createInsight({
      title: 'Likely-hate rate on 16 August',
      claim: '16 August: 6 of 31 Muslim-related items classified as likely hate, 19.4%.',
      numerator: 6,
      denominator: 31,
      metric: 'likely_hate_rate',
      from: '2026-08-16',
      to: '2026-08-16',
      explorerHref: '/app/explorer?from=2026-08-16&to=2026-08-16',
      figureLabel: 'Daily likely-hate rate, 2026-08-16',
      sources: ['youtube'],
      itemsObserved: 43,
      itemsRelevant: 31,
    });

    expect(insight.facts[0]?.numerator).toBe(6);
    expect(insight.facts[0]?.denominator).toBe(31);
    expect(insight.coverage.itemsRelevant).toBe(31);
    expect(insight.coverage.itemsObserved).toBe(43);
    expect(insight.generation.isMachineGenerated).toBe(false);
    expect(insight.coverage.warnings[0]).toMatch(/started from a figure/i);

    const thread = await fixtureProvider.getDiscussion(insight.id);
    expect(thread.posts).toHaveLength(0);

    const listed = await fixtureProvider.listInsights();
    expect(listed.insights[0]?.id).toBe(insight.id);
  });

  it('lists only the signed-in viewer notes', async () => {
    const notes = await fixtureProvider.listViewerPosts();

    expect(notes.posts.map((post) => post.id)).toEqual(['post_demo_window']);
    expect(notes.posts[0]?.insightTitle).toMatch(/collective-blame/i);
    expect(notes.posts.some((post) => post.id === 'post_amina_rate')).toBe(false);
  });
});

describe('fixtureProvider news', () => {
  it('returns window-scoped headlines without a hate classification', async () => {
    const list = await fixtureProvider.listNews({});

    expect(list.data_mode).toBe('fixture');
    expect(list.applied).toEqual({ from: '2026-07-18', to: '2026-08-16' });
    expect(list.items.map((item) => item.id)).toContain('news_bbc_0815');
    expect(list.items.map((item) => item.id)).not.toContain('news_pbs_0710');
    expect(list.items.map((item) => item.id)).not.toContain('news_globe_0820');
    expect(list.next_cursor).toBeNull();

    for (const item of list.items) {
      expect(item).not.toHaveProperty('classification');
      expect(item.title).not.toMatch(/classified as likely hate/i);
    }
  });

  it('narrows to the requested dates and treats a miss as a gap', async () => {
    const list = await fixtureProvider.listNews({
      from: '2026-06-18',
      to: '2026-06-20',
    });

    expect(list.items).toHaveLength(0);
    expect(list.coverage.items_retrieved).toBe(0);
    expect(list.coverage.warnings[0]).toMatch(/gap in the news stream/i);
  });
});

describe('fixtureProvider assistant', () => {
  it('answers from the same overview the dashboard uses', async () => {
    const reply = await fixtureProvider.askAssistant({
      question: 'What is the likely hate rate?',
    });

    expect(reply.groundedIn).toBe('figures');
    expect(reply.answer).toMatch(/18\.7%/);
    expect(reply.limitations[0]).toMatch(/stored figures/i);
  });
});

describe('fixtureProvider report draft', () => {
  it('prepares a YouTube email without sending it and without redacting the fixture line', async () => {
    const draft = await fixtureProvider.prepareReportDraft({
      platform: 'youtube',
      has_image: false,
    });

    expect(draft.to).toBe('report@youtube.example');
    expect(draft.status).toBe('prepared_not_sent');
    expect(draft.body).toMatch(/They don't belong here/i);
    expect(draft.body).not.toMatch(/\[Redacted/i);
  });
});

describe('fixtureProvider discussion', () => {
  beforeEach(() => {
    resetFixtureProvider();
  });

  it('returns the seeded thread for the fixture insight', async () => {
    const discussion = await fixtureProvider.getDiscussion('ins_collective_blame');

    expect(discussion.threadId).toBe('thr_collective_blame');
    expect(discussion.posts[0]?.body).toMatch(/gap days as gaps/i);
  });

  it('appends a note, records a useful reaction, and retracts the author post', async () => {
    const created = await fixtureProvider.createPost('ins_collective_blame', {
      body: 'The denominator is relevant items, not everything collected.',
      captureId: 'cap_daily_rate',
    });

    const authored = created.posts.find(
      (post) => post.body === 'The denominator is relevant items, not everything collected.',
    );
    expect(authored?.capture?.id).toBe('cap_daily_rate');
    expect(authored).toBeDefined();
    if (authored === undefined) {
      return;
    }

    const reacted = await fixtureProvider.reactToPost(authored.id, 'useful');
    const afterReact = reacted.posts.find((post) => post.id === authored.id);
    expect(afterReact?.reactions.useful).toBe(1);
    expect(afterReact?.reactions.viewer).toBe('useful');

    const retracted = await fixtureProvider.retractPost(authored.id);
    const afterRetract = retracted.posts.find((post) => post.id === authored.id);
    expect(afterRetract?.retractedAt).not.toBeNull();
    expect(afterRetract?.body).toBe('This note was retracted.');
    expect(afterRetract?.capture).toBeNull();
  });

  it("refuses to retract someone else's note", async () => {
    await expect(fixtureProvider.retractPost('post_amina_rate')).rejects.toThrow(
      'Only the author can retract a note.',
    );
  });
});

describe('fixtureProvider image examples', () => {
  it('lists the research corpus without an image payload', async () => {
    const list = await fixtureProvider.listImageExamples();

    expect(list.items).toHaveLength(42);
    expect(list.items[0]).not.toHaveProperty('image_data');
  });

  it('classifies from filename and size only', async () => {
    const result = await fixtureProvider.classifyEvidence({
      image_filename: 'img-ex-25.jpg',
      image_byte_size: 2048,
    });

    expect(result.example_id).toBe('img_ex_25');
    expect(result.classification).toBe('likely_hate');
    expect(result).not.toHaveProperty('image_data');
  });
});
