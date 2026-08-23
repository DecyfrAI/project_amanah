import { describe, expect, it } from 'vitest';

import { fixtureProvider } from '@/api/fixture-provider';

import { itemMatchesQuery, searchSuggestions } from '@/api/item-search';

describe('item search', () => {
  it('matches a comment item on a distinctive word', async () => {
    const page = await fixtureProvider.searchItems({});
    const council = page.items.find((item) => item.id === 'itm_4c1a');

    expect(council).toBeDefined();
    expect(itemMatchesQuery(council!, 'prayer')).toBe(true);
    expect(itemMatchesQuery(council!, 'iftar')).toBe(false);
  });

  it('matches an image item on form metadata rather than a slogan', async () => {
    const page = await fixtureProvider.searchItems({});
    const poster = page.items.find((item) => item.id === 'itm_img_01');

    expect(poster?.image?.filename).toBe('img-ex-01.png');
    expect(itemMatchesQuery(poster!, 'poster')).toBe(true);
    expect(itemMatchesQuery(poster!, 'img-ex-01')).toBe(true);
  });

  it('returns autocomplete suggestions only after two characters', async () => {
    const page = await fixtureProvider.searchItems({});

    expect(searchSuggestions(page.items, 'p')).toHaveLength(0);
    expect(searchSuggestions(page.items, 'prayer').some((item) => item.id === 'itm_4c1a')).toBe(
      true,
    );
  });
});
