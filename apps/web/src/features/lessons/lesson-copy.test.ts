import { describe, expect, it } from 'vitest';

import { collectActivityText, LESSON_ACTIVITY_PAGES } from './lesson-activities';
import {
  collectLessonHrefs,
  filterResources,
  getLessonCase,
  getLessonContent,
  getLessonModule,
  LESSON_CASES,
  LESSON_MODULES,
  LESSON_RESOURCES,
  lessonReaderPages,
  sourceOutboundHref,
} from './lesson-copy';

describe('lesson syllabus', () => {
  it('ships eight numbered modules with a thesis, chapters, and sources', () => {
    expect(LESSON_MODULES.map((module) => module.id)).toEqual([
      '01',
      '02',
      '03',
      '04',
      '05',
      '06',
      '07',
      '08',
    ]);

    for (const module of LESSON_MODULES) {
      expect(module.title.length).toBeGreaterThan(0);
      expect(module.thesis.length).toBeGreaterThan(0);
      expect(module.chapters.length).toBeGreaterThanOrEqual(3);
      expect(module.chapters.length).toBeLessThanOrEqual(5);
      expect(module.sources.length).toBeGreaterThan(0);
      const pages = lessonReaderPages(module);
      expect(pages.some((page) => page.kind === 'activity')).toBe(true);
      expect(pages.at(-1)?.title).toBe('Sources');
    }

    expect(LESSON_ACTIVITY_PAGES.map((page) => page.moduleId)).toEqual(
      LESSON_MODULES.map((module) => module.id),
    );
    for (const activity of LESSON_ACTIVITY_PAGES) {
      const module = getLessonModule(activity.moduleId);
      expect(module?.chapters.some((chapter) => chapter.id === activity.afterChapterId)).toBe(true);
    }
  });

  it('never claims causation with “caused by”', () => {
    const corpus = [
      ...LESSON_MODULES.flatMap((module) => [
        module.thesis,
        ...module.chapters.flatMap((chapter) => chapter.paragraphs),
        ...module.sources.map((source) => source.note ?? ''),
      ]),
      ...LESSON_CASES.flatMap((entry) => [
        entry.thesis,
        ...entry.chapters.flatMap((chapter) => chapter.paragraphs),
        ...entry.sources.map((source) => source.note ?? ''),
      ]),
      collectActivityText(),
    ].join(' ');

    expect(corpus).not.toMatch(/caused by/i);
  });

  it('does not link to 4chan or 8chan', () => {
    const hrefs = [...collectLessonHrefs(), ...collectLessonHrefs(LESSON_CASES)].join('\n');
    expect(hrefs).not.toMatch(/4chan|8chan|8kun/i);
  });

  it('ships public cases with generated stills, sources, and the online-radicalization set', () => {
    const ids = LESSON_CASES.map((entry) => entry.id);
    expect(ids).toEqual([
      'isla-vista',
      'quebec',
      'toronto',
      'pittsburgh',
      'christchurch',
      'california',
      'el-paso',
      'plymouth',
      'buffalo',
      'halle',
      'baerum',
      'finsbury-park',
    ]);
    for (const entry of LESSON_CASES) {
      expect(entry.track).toBe('case');
      expect(entry.hero?.src.startsWith('/media/cases/')).toBe(true);
      expect(entry.chapters.some((chapter) => chapter.visual === 'case-media')).toBe(true);
      expect(entry.sources.length).toBeGreaterThan(0);
      expect(
        entry.sources.every((source) => source.href !== undefined || source.doi !== undefined),
      ).toBe(true);
      expect(getLessonContent(entry.id)?.id).toBe(entry.id);
    }
    expect(getLessonCase('99')).toBeUndefined();
  });

  it('returns undefined for an id outside the syllabus', () => {
    expect(getLessonModule('99')).toBeUndefined();
    expect(getLessonModule('mod_islamophobia')).toBeUndefined();
  });

  it('prefers a DOI landing page when both a DOI and a copy exist', () => {
    const source = LESSON_MODULES[0]?.sources[0];
    expect(source?.doi).toBe('10.1037/amp0000062');
    expect(sourceOutboundHref(source!)).toBe('https://doi.org/10.1037/amp0000062');
  });

  it('stores the fields the resource contract requires', () => {
    expect(LESSON_RESOURCES.length).toBeGreaterThanOrEqual(13);
    for (const resource of LESSON_RESOURCES) {
      expect(resource.title.length).toBeGreaterThan(0);
      expect(resource.organization.length).toBeGreaterThan(0);
      expect(resource.href.startsWith('https://')).toBe(true);
      expect(resource.lastReviewed).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(resource.reviewer.length).toBeGreaterThan(0);
    }
  });

  it('includes support lines for Canada, the United States, and the United Kingdom', () => {
    const support = LESSON_RESOURCES.filter((resource) => resource.category === 'support');
    expect(support.some((resource) => resource.scope === 'ca')).toBe(true);
    expect(support.some((resource) => resource.scope === 'us')).toBe(true);
    expect(support.some((resource) => resource.scope === 'uk')).toBe(true);
  });

  it('keeps international resources when a country is selected', () => {
    const usSupport = filterResources(LESSON_RESOURCES, 'support', 'us');
    expect(usSupport.some((resource) => resource.id === 'res_988')).toBe(true);
    expect(usSupport.some((resource) => resource.id === 'res_iasp')).toBe(true);
    expect(usSupport.some((resource) => resource.id === 'res_samaritans')).toBe(false);
  });

  it('returns an empty list when a country has no row in that category', () => {
    const usInvolved = filterResources(LESSON_RESOURCES, 'involved', 'us');
    expect(usInvolved).toEqual([]);
  });

  it('does not link resources to 4chan or 8chan', () => {
    const hrefs = LESSON_RESOURCES.map((resource) => resource.href).join('\n');
    expect(hrefs).not.toMatch(/4chan|8chan|8kun/i);
  });

  it('sources YouTube and Reddit policy and report pages, not invented inboxes', () => {
    const byId = Object.fromEntries(LESSON_RESOURCES.map((resource) => [resource.id, resource]));

    expect(byId.res_youtube_guidelines?.href).toBe(
      'https://support.google.com/youtube/answer/9288567',
    );
    expect(byId.res_youtube_hate?.href).toBe('https://support.google.com/youtube/answer/2801939');
    expect(byId.res_youtube_report?.href).toBe('https://support.google.com/youtube/answer/2802027');
    expect(byId.res_reddit_policy?.href).toBe('https://www.redditinc.com/policies/content-policy');
    expect(byId.res_reddit_hate?.href).toBe(
      'https://support.reddithelp.com/hc/en-us/articles/360045715951-Promoting-Hate-Based-on-Identity-or-Vulnerability',
    );
    expect(byId.res_reddit_report?.href).toBe('https://www.reddit.com/report');

    const summaries = LESSON_RESOURCES.map((resource) => resource.summary).join('\n');
    expect(summaries).not.toMatch(/report@youtube\.com|report@reddit\.com|legal@reddit\.com/i);
  });
});
