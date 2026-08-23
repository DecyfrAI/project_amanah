import { describe, expect, it } from 'vitest';

import { fixtureProvider } from '@/api/fixture-provider';

import { replyFromOverview } from './ask-reply';

describe('replyFromOverview', () => {
  it('cites the likely-hate rate already on the overview', async () => {
    const overview = await fixtureProvider.getOverview({});
    const reply = replyFromOverview('What is the likely hate rate?', overview);

    expect(reply.groundedIn).toBe('figures');
    expect(reply.answer).toMatch(/18\.7%/);
    expect(reply.answer).toMatch(/253/);
    expect(reply.answer).toMatch(/1,350/);
    expect(reply.citations[0]?.id).toBe('rate');
  });

  it('cites coverage rather than inventing a sample size', async () => {
    const overview = await fixtureProvider.getOverview({});
    const reply = replyFromOverview('What does this sample cover?', overview);

    expect(reply.groundedIn).toBe('figures');
    expect(reply.answer).toMatch(/1,350/);
    expect(reply.answer).toMatch(/5,491/);
    expect(reply.citations[0]?.kind).toBe('coverage');
  });

  it('refuses a question that names no stored figure', async () => {
    const overview = await fixtureProvider.getOverview({});
    const reply = replyFromOverview('Who is the worst repeat offender this week?', overview);

    expect(reply.groundedIn).toBe('none');
    expect(reply.answer).toMatch(/will not invent/i);
    expect(reply.citations).toHaveLength(0);
  });

  it('cites daily movement without treating a gap as zero', async () => {
    const overview = await fixtureProvider.getOverview({});
    const reply = replyFromOverview(
      'How did the likely-hate rate move over this window?',
      overview,
    );

    expect(reply.groundedIn).toBe('figures');
    expect(reply.answer).toMatch(/highest collected daily rate/i);
    expect(reply.answer).toMatch(/gap/i);
    expect(reply.answer).not.toMatch(/caused by/i);
  });

  it('treats news as coinciding context, not a cause', async () => {
    const overview = await fixtureProvider.getOverview({});
    const news = await fixtureProvider.listNews({});
    const reply = replyFromOverview('Which news items coincide with this window?', overview, {
      news: news.items,
      items: [],
    });

    expect(reply.groundedIn).toBe('figures');
    expect(reply.answer).toMatch(/coinciding context/i);
    expect(reply.answer).toMatch(/not a cause/i);
    expect(reply.answer).toContain(news.items[0]?.title ?? 'missing');
  });

  it('walks through one explorer entry without an author', async () => {
    const overview = await fixtureProvider.getOverview({});
    const page = await fixtureProvider.searchItems({});
    const first = page.items[0];
    expect(first).toBeDefined();
    if (first === undefined) {
      return;
    }

    const reply = replyFromOverview(
      'Walk me through one explorer entry from this sample.',
      overview,
      {
        news: [],
        items: page.items,
      },
    );

    expect(reply.groundedIn).toBe('figures');
    expect(reply.answer).toContain(first.id);
    expect(reply.answer).toMatch(/classified as likely/i);
    expect(reply.answer).toMatch(/no author field/i);
  });
});
