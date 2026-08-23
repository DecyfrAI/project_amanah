import type { ExplorerItem } from './contracts';

/**
 * Fields a keyword query may match. Form notes and filenames are included so
 * image posts can be found without relying on comment wording.
 */
export function itemSearchHaystack(item: ExplorerItem): string {
  return [
    item.id,
    item.date,
    item.platform,
    item.containerTitle,
    item.redactedExcerpt,
    item.hateType,
    item.classification,
    item.reviewState,
    item.image?.filename,
    item.image?.formNote,
    item.image?.exampleId,
  ]
    .filter((part): part is string => part !== null && part !== undefined && part.length > 0)
    .join(' ')
    .toLowerCase();
}

export function itemMatchesQuery(item: ExplorerItem, query: string | undefined): boolean {
  const tokens = (query ?? '')
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter((token) => token.length > 0);

  if (tokens.length === 0) {
    return true;
  }

  const haystack = itemSearchHaystack(item);
  return tokens.every((token) => haystack.includes(token));
}

export function searchSuggestions(
  items: readonly ExplorerItem[],
  query: string,
  limit = 6,
): readonly ExplorerItem[] {
  const trimmed = query.trim();
  if (trimmed.length < 2) {
    return [];
  }

  return items.filter((item) => itemMatchesQuery(item, trimmed)).slice(0, limit);
}
