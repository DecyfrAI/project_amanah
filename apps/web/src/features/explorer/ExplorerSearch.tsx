import { useCallback, useId, useMemo, useState, type ChangeEvent, type FormEvent } from 'react';

import type { ExplorerItem } from '@/api';
import { searchSuggestions } from '@/api/item-search';

import styles from './ExplorerSearch.module.css';

interface ExplorerSearchProps {
  value: string;
  items: readonly ExplorerItem[];
  onQueryChange: (query: string) => void;
}

export function ExplorerSearch({ value, items, onQueryChange }: ExplorerSearchProps) {
  const listId = useId();
  const [draft, setDraft] = useState(value);
  const suggestions = useMemo(() => searchSuggestions(items, draft), [draft, items]);

  const handleChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setDraft(event.currentTarget.value);
  }, []);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      onQueryChange(draft);
    },
    [draft, onQueryChange],
  );

  return (
    <search className={styles.form}>
      <form onSubmit={handleSubmit}>
        <label className={styles.label} htmlFor="explorer-search">
          Search records
        </label>
        <p className={styles.hint} id="explorer-search-hint">
          Keywords match titles, excerpts, and image metadata. An empty result is not a quiet day.
        </p>
        <div className={styles.row}>
          <input
            id="explorer-search"
            className={styles.input}
            type="search"
            name="q"
            value={draft}
            onChange={handleChange}
            autoComplete="off"
            aria-describedby="explorer-search-hint"
            list={listId}
          />
          <button className={styles.submit} type="submit">
            Search
          </button>
        </div>
        <datalist id={listId}>
          {suggestions.map((item) => (
            <option
              key={item.id}
              value={
                item.image !== undefined && item.image !== null
                  ? item.image.formNote
                  : item.containerTitle
              }
            >
              {item.date}
              {item.image !== undefined && item.image !== null ? ' · image' : ''}
            </option>
          ))}
        </datalist>
      </form>
    </search>
  );
}
