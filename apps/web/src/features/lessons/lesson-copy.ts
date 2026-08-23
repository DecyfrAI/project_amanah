/**
 * Syllabus helpers and the reviewed external resource catalog (F-S15).
 *
 * Module cards and reader pages come from `lesson-modules.ts`. Resources are
 * the spec 9.12 starter set: Bridge, Tell MAMA, CAIR, NCCM, platform reporting,
 * research, crisis lines, and getting involved. They are not Amanah findings.
 */

import { getLessonActivityPage } from './lesson-activities';
import { LESSON_CASES } from './lesson-cases';
import {
  LESSON_MODULES,
  type LessonChapter,
  type LessonMedia,
  type LessonModule,
  type LessonSource,
} from './lesson-modules';

export { LESSON_CASES } from './lesson-cases';
export {
  LESSON_CASE_NOTE,
  LESSON_MODULES,
  LESSON_RESEARCH_NOTE,
  type LessonChapter,
  type LessonMedia,
  type LessonModule,
  type LessonSource,
} from './lesson-modules';

export const RESOURCE_CATEGORIES = [
  'all',
  'understanding',
  'research',
  'responding',
  'reporting',
  'support',
  'involved',
] as const;

export const RESOURCE_SCOPES = ['all', 'international', 'ca', 'us', 'uk'] as const;

export type ResourceCategory = Exclude<(typeof RESOURCE_CATEGORIES)[number], 'all'>;
export type ResourceScope = Exclude<(typeof RESOURCE_SCOPES)[number], 'all'>;
export type ResourceCategoryFilter = (typeof RESOURCE_CATEGORIES)[number];
export type ResourceScopeFilter = (typeof RESOURCE_SCOPES)[number];

export interface LessonResource {
  readonly id: string;
  readonly title: string;
  readonly organization: string;
  readonly href: string;
  readonly scope: ResourceScope;
  readonly category: ResourceCategory;
  readonly summary: string;
  readonly lastReviewed: string;
  readonly reviewer: string;
}

export interface LessonReaderPage {
  readonly id: string;
  readonly title: string;
  readonly kind: 'chapter' | 'sources' | 'activity';
  readonly paragraphs: readonly string[];
  readonly visual?: LessonChapter['visual'];
  readonly media?: LessonMedia;
}

export const CATEGORY_LABELS: Record<ResourceCategoryFilter, string> = {
  all: 'Every category',
  understanding: 'Understanding Islamophobia',
  research: 'Research and data',
  responding: 'Responding to online hate',
  reporting: 'Platform reporting',
  support: 'Support for affected people',
  involved: 'Getting involved',
};

export const SCOPE_LABELS: Record<ResourceScopeFilter, string> = {
  all: 'Every place',
  international: 'International',
  ca: 'Canada',
  us: 'United States',
  uk: 'United Kingdom',
};

/**
 * Reviewed starter catalog. URLs are official organization pages from spec
 * 9.12 / §28 or the previous Lessons list. Last-reviewed dates are fixture
 * reviews, not live crawls.
 */
export const LESSON_RESOURCES: readonly LessonResource[] = [
  {
    id: 'res_bridge',
    title: 'Islamophobia Resource Center',
    organization: 'Georgetown University Bridge Initiative',
    href: 'https://bridge.georgetown.edu/projects/resource-center/',
    scope: 'international',
    category: 'understanding',
    summary:
      'Explainers and a working definition of Islamophobia, kept as a research project rather than as a news feed.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_cair_research',
    title: 'Research and civil-rights materials',
    organization: 'Council on American-Islamic Relations',
    href: 'https://www.cair.com/',
    scope: 'us',
    category: 'research',
    summary:
      "US civil-rights reporting and research on anti-Muslim incidents. Use the organization's own pages for current figures.",
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_cair_california',
    title: 'California civil-rights reports',
    organization: 'CAIR California',
    href: 'https://ca.cair.com/reports/',
    scope: 'us',
    category: 'research',
    summary:
      'State-level reports cited in the specification. California-specific; not a national rate.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_nccm',
    title: 'Publications and community resources',
    organization: 'National Council of Canadian Muslims',
    href: 'https://nccm.ca/publications/',
    scope: 'ca',
    category: 'research',
    summary:
      'Canadian advocacy, research, and community guidance. Country-specific; not a substitute for local legal advice.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_tellmama',
    title: 'Resources and reporting guidance',
    organization: 'Tell MAMA',
    href: 'https://tellmamauk.org/resources/',
    scope: 'uk',
    category: 'responding',
    summary:
      'UK materials on recording and responding to anti-Muslim hate. Tell MAMA also takes reports from people who want a record kept.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_youtube_guidelines',
    title: 'Community Guidelines',
    organization: 'YouTube',
    href: 'https://support.google.com/youtube/answer/9288567',
    scope: 'international',
    category: 'reporting',
    summary:
      'The platform-wide rules that sit above the hate-speech article. YouTube does not publish a public mailbox for ordinary reports.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_youtube_hate',
    title: 'Hate speech policy',
    organization: 'YouTube',
    href: 'https://support.google.com/youtube/answer/2801939',
    scope: 'international',
    category: 'reporting',
    summary:
      'How YouTube defines hate speech and what a person can report. Amanah never submits a report for you.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_youtube_report',
    title: 'Report inappropriate content',
    organization: 'YouTube',
    href: 'https://support.google.com/youtube/answer/2802027',
    scope: 'international',
    category: 'reporting',
    summary: 'Step-by-step reporting on YouTube. A person still has to send the report.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_reddit_policy',
    title: 'Reddit Rules',
    organization: 'Reddit',
    href: 'https://www.redditinc.com/policies/content-policy',
    scope: 'international',
    category: 'reporting',
    summary:
      'The sitewide content policy, including the rule against promoting hate based on identity or vulnerability. Reddit does not publish a public mailbox for ordinary reports.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_reddit_hate',
    title: 'Promoting hate based on identity or vulnerability',
    organization: 'Reddit',
    href: 'https://support.reddithelp.com/hc/en-us/articles/360045715951-Promoting-Hate-Based-on-Identity-or-Vulnerability',
    scope: 'international',
    category: 'reporting',
    summary:
      'How Reddit explains the hate rule in the Content Policy. Use it to decide whether a report is on-policy. Amanah never submits one for you.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_reddit_report',
    title: 'Report a post or comment',
    organization: 'Reddit',
    href: 'https://www.reddit.com/report',
    scope: 'international',
    category: 'reporting',
    summary:
      'The official report form. If you have an account, you can also use Report on the post or comment. A person still has to send the report.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_988',
    title: '988 Suicide and Crisis Lifeline',
    organization: '988 Lifeline',
    href: 'https://988lifeline.org/',
    scope: 'us',
    category: 'support',
    summary:
      'Call or text 988 in the United States for a trained counselor. This is a crisis line, not a hate-incident desk.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_talk_suicide',
    title: 'Talk Suicide Canada',
    organization: 'Talk Suicide Canada',
    href: 'https://talksuicide.ca/',
    scope: 'ca',
    category: 'support',
    summary: 'Call 1-833-456-4566 in Canada. 24-hour support. This is a crisis line.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_samaritans',
    title: 'Samaritans',
    organization: 'Samaritans',
    href: 'https://www.samaritans.org/',
    scope: 'uk',
    category: 'support',
    summary: 'Call 116 123 in the United Kingdom. Free, 24-hour. This is a crisis line.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_iasp',
    title: 'Find a local helpline',
    organization: 'International Association for Suicide Prevention',
    href: 'https://www.iasp.info/suicidalthoughts/',
    scope: 'international',
    category: 'support',
    summary:
      'A directory of crisis lines by country, for anyone who is not in the US, Canada, or the UK.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_cair_report',
    title: 'Report a civil-rights incident',
    organization: 'Council on American-Islamic Relations',
    href: 'https://www.cair.com/report/',
    scope: 'us',
    category: 'support',
    summary:
      'A US intake path for discrimination, harassment, or a hate incident. CAIR is an advocacy organization, not emergency services.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_tellmama_report',
    title: 'Report an anti-Muslim incident',
    organization: 'Tell MAMA',
    href: 'https://tellmamauk.org/',
    scope: 'uk',
    category: 'support',
    summary: 'UK reporting and support for anti-Muslim hate, online or offline.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
  {
    id: 'res_nccm_involved',
    title: 'Get involved',
    organization: 'National Council of Canadian Muslims',
    href: 'https://nccm.ca/',
    scope: 'ca',
    category: 'involved',
    summary:
      'Canadian campaigns, community work, and publications. Involvement is local; this link is a starting point, not a signup for Amanah.',
    lastReviewed: '2026-08-23',
    reviewer: 'Amanah editorial (fixture)',
  },
];

export function isResourceCategoryFilter(value: string): value is ResourceCategoryFilter {
  return (RESOURCE_CATEGORIES as readonly string[]).includes(value);
}

export function isResourceScopeFilter(value: string): value is ResourceScopeFilter {
  return (RESOURCE_SCOPES as readonly string[]).includes(value);
}

export function filterResources(
  resources: readonly LessonResource[],
  category: ResourceCategoryFilter,
  scope: ResourceScopeFilter,
): LessonResource[] {
  return resources.filter((resource) => {
    const categoryMatch = category === 'all' || resource.category === category;
    const scopeMatch =
      scope === 'all' || resource.scope === scope || resource.scope === 'international';
    return categoryMatch && scopeMatch;
  });
}

export function getLessonModule(id: string): LessonModule | undefined {
  return LESSON_MODULES.find((module) => module.id === id);
}

export function getLessonCase(id: string): LessonModule | undefined {
  return LESSON_CASES.find((entry) => entry.id === id);
}

export function getLessonContent(id: string): LessonModule | undefined {
  return getLessonModule(id) ?? getLessonCase(id);
}

export function lessonCatalogPath(publicRoute: boolean): string {
  return publicRoute ? '/resources' : '/app/lessons';
}

export function lessonReaderPath(id: string, publicRoute: boolean): string {
  return `${lessonCatalogPath(publicRoute)}/${id}`;
}

export function lessonReaderPages(module: LessonModule): LessonReaderPage[] {
  const activity = getLessonActivityPage(module.id);
  const pages: LessonReaderPage[] = [];

  for (const chapter of module.chapters) {
    pages.push(toChapterPage(chapter));
    if (activity !== undefined && activity.afterChapterId === chapter.id) {
      pages.push(toActivityPage(activity));
    }
  }

  if (activity !== undefined && pages.every((page) => page.kind !== 'activity')) {
    pages.push(toActivityPage(activity));
  }

  pages.push({
    id: `${module.id}-sources`,
    title: 'Sources',
    kind: 'sources',
    paragraphs: [],
  });

  return pages;
}

function toChapterPage(chapter: LessonChapter): LessonReaderPage {
  return {
    id: chapter.id,
    title: chapter.title,
    kind: 'chapter',
    paragraphs: chapter.paragraphs,
    ...(chapter.visual === undefined ? {} : { visual: chapter.visual }),
    ...(chapter.media === undefined ? {} : { media: chapter.media }),
  };
}

function toActivityPage(activity: { id: string; title: string }): LessonReaderPage {
  return {
    id: activity.id,
    title: activity.title,
    kind: 'activity',
    paragraphs: [],
  };
}

export function sourceOutboundHref(source: LessonSource): string | undefined {
  if (source.doi !== undefined) {
    return `https://doi.org/${source.doi}`;
  }
  return source.href;
}

export function isExternalHref(href: string): boolean {
  return href.startsWith('http://') || href.startsWith('https://');
}

export function externalLinkProps(href: string): { target?: string; rel?: string } {
  if (!isExternalHref(href)) {
    return {};
  }
  return { target: '_blank', rel: 'noopener noreferrer' };
}

export function collectLessonHrefs(modules: readonly LessonModule[] = LESSON_MODULES): string[] {
  const hrefs: string[] = [];
  for (const module of modules) {
    for (const source of module.sources) {
      const outbound = sourceOutboundHref(source);
      if (outbound !== undefined) {
        hrefs.push(outbound);
      }
      if (source.href !== undefined) {
        hrefs.push(source.href);
      }
    }
  }
  return hrefs;
}
