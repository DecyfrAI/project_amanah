import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  classifyEvidenceFixture,
  loadImageExampleList,
  pickImageExample,
} from './image-classification';

const SLUR = /nigger|kike|paki|raghead|goat.?fuck/i;

describe('research image datapack', () => {
  it('validates forty-two sourced examples against the contract', () => {
    const list = loadImageExampleList('fixture');

    expect(list.items).toHaveLength(42);
    expect(list.manifest?.dataset_name).toBe('research-islamophobia-image-corpus');
    expect(list.data_mode).toBe('fixture');
  });

  it('points each row at a file that exists in the repo', () => {
    const list = loadImageExampleList();
    const publicRoot = resolve(process.cwd(), 'public');

    for (const item of list.items) {
      expect(item.image_src.startsWith('/media/fixtures/memes/img-ex-')).toBe(true);
      expect(existsSync(resolve(publicRoot, item.image_src.slice(1)))).toBe(true);
    }
  });

  it('keeps slogans out of titles, alt text, and notes', () => {
    const list = loadImageExampleList();

    for (const item of list.items) {
      const blob = [item.title, item.alt_text, item.form_note, item.rationale].join('\n');
      expect(blob).not.toMatch(SLUR);
      expect(item.alt_text).toMatch(/Harmful research example/i);
    }
  });

  it('picks a named example from a filename slug and does not need pixels', () => {
    const example = pickImageExample('img-ex-31.jpg');

    expect(example.id).toBe('img_ex_31');
    const result = classifyEvidenceFixture({
      image_filename: 'img-ex-31.jpg',
      example_id: 'img_ex_31',
    });
    expect(result.classification).toBe('likely_hate');
    expect(result.review_required).toBe(true);
    expect(result.disclosure).toMatch(/did not read pixels/i);
    expect(result).not.toHaveProperty('image_data');
  });
});
