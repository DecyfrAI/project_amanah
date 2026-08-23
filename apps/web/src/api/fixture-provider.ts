import { replyFromOverview } from '@/features/ask/ask-reply';
import { readFixtureSession } from '@/features/auth/session';
import { prepareReportDraft as buildReportDraft } from '@/features/reports/prepare-report-draft';
import { classifyEvidenceFixture, loadImageExampleList } from './image-classification';

import { FIXTURE_VIEWER, type ApiClient, type NewsFilters, type OverviewFilters } from './client';
import { itemMatchesQuery } from './item-search';
import {
  AssistantAskInputSchema,
  AssistantReplySchema,
  CreateCaptureInputSchema,
  CreateInsightInputSchema,
  CreatePostInputSchema,
  DiscussionCatalogSchema,
  ExplorerItemSchema,
  ExplorerPageSchema,
  FilterOptionsSchema,
  InsightListSchema,
  InsightSchema,
  NewsItemSchema,
  NewsListSchema,
  OverviewSchema,
  EvidenceClassifyRequestSchema,
  ImageClassificationSchema,
  ImageExampleListSchema,
  ReportDraftRequestSchema,
  ReportDraftSchema,
  ViewerPostListSchema,
  type AssistantAskInput,
  type AssistantReply,
  type CreateCaptureInput,
  type CreateInsightInput,
  type CreatePostInput,
  type DashboardCapture,
  type Discussion,
  type ExplorerItem,
  type ExplorerPage,
  type FilterOptions,
  type Insight,
  type InsightList,
  type NewsItem,
  type NewsList,
  type Overview,
  type ReactionKind,
  type EvidenceClassifyRequest,
  type ImageClassification,
  type ImageExampleList,
  type ReportDraft,
  type ReportDraftRequest,
  type ViewerPostList,
} from './contracts';
import { ApiRequestError } from './errors';
import {
  appliedFilters,
  deriveFilterOptions,
  deriveOverview,
  resolveWindow,
  type CollectionDocument,
} from './fixture-derive';

import collectionJson from '@/fixtures/collection.json' with { type: 'json' };
import discussionsJson from '@/fixtures/discussions.json' with { type: 'json' };
import insightsJson from '@/fixtures/insights.json' with { type: 'json' };
import itemsJson from '@/fixtures/items.json' with { type: 'json' };
import newsJson from '@/fixtures/news.json' with { type: 'json' };

let insightsCatalog: InsightList = InsightListSchema.parse(insightsJson);

/**
 * The generated day-level fixture, filtered and aggregated here exactly as the
 * live service would do server-side. Deriving rather than storing a canned
 * response is what makes the filters real: the same request produces the same
 * figures in both modes, so flipping VITE_DATA_MODE changes nothing on screen.
 */
const collection = collectionJson as unknown as CollectionDocument;

const explorerItems: readonly ExplorerItem[] = ExplorerItemSchema.array().parse(itemsJson.items);

const newsCatalog: readonly NewsItem[] = NewsItemSchema.array().parse(newsJson.items);
const newsLastRun =
  typeof newsJson.last_successful_run === 'string' ? newsJson.last_successful_run : null;

/** Newest first, with the id as a stable secondary ordering. */
const orderedItems = explorerItems.toSorted((left, right) =>
  left.date === right.date ? left.id.localeCompare(right.id) : right.date.localeCompare(left.date),
);

const EXPLORER_PAGE_SIZE = 25;
let discussionCatalog: Discussion[] = [];
const captures = new Map<string, DashboardCapture>();

function seedCatalog(): void {
  discussionCatalog = DiscussionCatalogSchema.parse(discussionsJson).threads.map((thread) =>
    structuredClone(thread),
  );
  captures.clear();
  for (const thread of discussionCatalog) {
    for (const post of thread.posts) {
      if (post.capture !== null) {
        captures.set(post.capture.id, structuredClone(post.capture));
      }
    }
  }
}

seedCatalog();

function seedInsights(): void {
  insightsCatalog = InsightListSchema.parse(structuredClone(insightsJson));
}

export function resetFixtureProvider(): void {
  seedInsights();
  seedCatalog();
}

function viewerAuthor(): { id: string; displayName: string } {
  return {
    id: FIXTURE_VIEWER.id,
    displayName: readFixtureSession()?.displayName ?? FIXTURE_VIEWER.displayName,
  };
}

function findThread(insightId: string): Discussion {
  const thread = discussionCatalog.find((entry) => entry.insightId === insightId);
  if (thread === undefined) {
    throw new ApiRequestError('That insight has no discussion thread.', 404);
  }
  return thread;
}

function findPost(postId: string): { thread: Discussion; postIndex: number } {
  for (const thread of discussionCatalog) {
    const postIndex = thread.posts.findIndex((post) => post.id === postId);
    if (postIndex !== -1) {
      return { thread, postIndex };
    }
  }
  throw new ApiRequestError('That note could not be found.', 404);
}

function cloneDiscussion(thread: Discussion): Discussion {
  return structuredClone(thread);
}

function matchesFilters(item: ExplorerItem, applied: ReturnType<typeof appliedFilters>): boolean {
  if (item.date < applied.from || item.date > applied.to) {
    return false;
  }
  if (applied.platforms.length > 0 && !applied.platforms.includes(item.platform)) {
    return false;
  }
  if (
    applied.hateTypes.length > 0 &&
    (item.hateType === null || !applied.hateTypes.includes(item.hateType))
  ) {
    return false;
  }
  if (
    applied.severityBands.length > 0 &&
    (item.severity === null || !applied.severityBands.includes(String(item.severity)))
  ) {
    return false;
  }
  if (applied.reviewStates.length > 0 && !applied.reviewStates.includes(item.reviewState)) {
    return false;
  }
  return true;
}

export const fixtureProvider: ApiClient = {
  /**
   * Derived from the generated collection fixture under the filters given, so a
   * narrower window or a platform selection really does change the figures. The
   * response states its own window and coverage, and the UI reads those rather
   * than the request, so the screen never claims a window it lacks data for.
   */
  async getOverview(filters: OverviewFilters): Promise<Overview> {
    return OverviewSchema.parse(deriveOverview(collection, filters));
  },

  async getFilterOptions(): Promise<FilterOptions> {
    return FilterOptionsSchema.parse(deriveFilterOptions(collection));
  },

  /**
   * Published news that coincides with the same date window as Overview.
   *
   * Platform and taxonomy filters are ignored: an article is context, not a
   * classified item. `published_at` is compared on its UTC calendar date so a
   * headline lands in the window the figures describe. A failed ingest is a
   * gap, never a zero count invented here.
   */
  async listNews(filters: NewsFilters): Promise<NewsList> {
    const window = resolveWindow(collection, { from: filters.from, to: filters.to });
    const matched = newsCatalog
      .filter((item) => {
        const day = item.published_at.slice(0, 10);
        return day >= window.from && day <= window.to;
      })
      .toSorted((left, right) =>
        left.published_at === right.published_at
          ? left.id.localeCompare(right.id)
          : right.published_at.localeCompare(left.published_at),
      );

    const sources = [...new Set(matched.map((item) => item.source_name))].toSorted();

    return NewsListSchema.parse({
      window: { from: window.from, to: window.to, timezone: collection.available.timezone },
      applied: { from: window.from, to: window.to },
      coverage: {
        sources,
        items_retrieved: matched.length,
        last_successful_run: newsLastRun,
        warnings:
          matched.length === 0
            ? [
                'No ingested article has a publication date in this window. That is a gap in the news stream, not a claim that nothing happened.',
              ]
            : [],
      },
      data_mode: 'fixture',
      next_cursor: null,
      items: structuredClone(matched),
    });
  },

  /**
   * Item-level results for the Explorer.
   *
   * The fixture carries far fewer items than the aggregate counts describe, which
   * is deliberate and stated on screen: these are reviewed examples, not the
   * whole collection, and `matched` is the count of examples rather than a claim
   * about the corpus.
   */
  async searchItems(filters: OverviewFilters): Promise<ExplorerPage> {
    const applied = appliedFilters(collection, filters);
    const matched = orderedItems.filter(
      (item) => matchesFilters(item, applied) && itemMatchesQuery(item, filters.q),
    );
    const page = matched.slice(0, EXPLORER_PAGE_SIZE);

    return ExplorerPageSchema.parse({
      applied,
      matched: matched.length,
      returned: page.length,
      items: structuredClone(page),
    });
  },

  async listInsights(): Promise<InsightList> {
    return structuredClone(insightsCatalog);
  },

  async getInsight(insightId: string): Promise<Insight> {
    const insight = insightsCatalog.insights.find((entry) => entry.id === insightId);
    if (insight === undefined) {
      throw new ApiRequestError('That insight could not be found.', 404);
    }
    return structuredClone(insight);
  },

  /**
   * A viewer-created snapshot of one figure or one day.
   *
   * The thread is created empty so colleagues can attach notes to the same
   * finding. Coverage is the counts on the figure, not a fresh collection run,
   * and the warning says so.
   */
  async createInsight(input: CreateInsightInput): Promise<Insight> {
    const parsed = CreateInsightInputSchema.parse(input);
    const now = new Date().toISOString();
    const insight = InsightSchema.parse({
      id: `ins_${crypto.randomUUID()}`,
      title: parsed.title,
      summary: parsed.claim,
      window: { from: parsed.from, to: parsed.to, timezone: 'UTC' },
      coverage: {
        sources: parsed.sources,
        itemsObserved: parsed.itemsObserved,
        itemsRelevant: parsed.itemsRelevant,
        lastSuccessfulRun: null,
        warnings: [
          'This snapshot was started from a figure. The counts are those on the figure at the time, not a new collection run.',
        ],
      },
      facts: [
        {
          id: `fact_${crypto.randomUUID()}`,
          claim: parsed.claim,
          numerator: parsed.numerator,
          denominator: parsed.denominator,
          metric: parsed.metric,
        },
      ],
      citations: [
        {
          kind: 'figure',
          id: 'fig_snapshot',
          label: parsed.figureLabel,
        },
        {
          kind: 'item',
          id: 'explorer_scope',
          label: parsed.explorerHref,
        },
      ],
      generation: {
        model: 'viewer-snapshot',
        generatedAt: now,
        isMachineGenerated: false,
      },
    });

    insightsCatalog = { insights: [insight, ...insightsCatalog.insights] };
    discussionCatalog.push({
      insightId: insight.id,
      threadId: `thr_${crypto.randomUUID()}`,
      posts: [],
    });

    return structuredClone(insight);
  },

  async listViewerPosts(): Promise<ViewerPostList> {
    const posts = [];
    for (const thread of discussionCatalog) {
      const insight = insightsCatalog.insights.find((entry) => entry.id === thread.insightId);
      for (const post of thread.posts) {
        if (post.author.id !== FIXTURE_VIEWER.id) {
          continue;
        }
        posts.push({
          ...post,
          insightId: thread.insightId,
          insightTitle: insight?.title ?? 'Untitled insight',
        });
      }
    }

    const ordered = posts.toSorted((left, right) => right.createdAt.localeCompare(left.createdAt));
    return ViewerPostListSchema.parse({ posts: structuredClone(ordered) });
  },

  async getDiscussion(insightId: string): Promise<Discussion> {
    return cloneDiscussion(findThread(insightId));
  },

  async createPost(insightId: string, input: CreatePostInput): Promise<Discussion> {
    const parsed = CreatePostInputSchema.parse(input);
    const thread = findThread(insightId);
    const capture =
      parsed.captureId === undefined ? null : (captures.get(parsed.captureId) ?? null);

    if (parsed.captureId !== undefined && capture === null) {
      throw new ApiRequestError('That figure is not available to attach.', 400);
    }

    thread.posts.push({
      id: `post_${crypto.randomUUID()}`,
      author: viewerAuthor(),
      body: parsed.body,
      createdAt: new Date().toISOString(),
      retractedAt: null,
      capture: capture === null ? null : structuredClone(capture),
      reactions: { useful: 0, needs_context: 0, viewer: null },
    });

    return cloneDiscussion(thread);
  },

  async reactToPost(postId: string, kind: ReactionKind): Promise<Discussion> {
    const { thread, postIndex } = findPost(postId);
    const post = thread.posts[postIndex];
    if (post === undefined || post.retractedAt !== null) {
      throw new ApiRequestError('That note can no longer receive a reaction.', 409);
    }

    const current = post.reactions.viewer;
    if (current === kind) {
      post.reactions[kind] = Math.max(0, post.reactions[kind] - 1);
      post.reactions.viewer = null;
    } else {
      if (current !== null) {
        post.reactions[current] = Math.max(0, post.reactions[current] - 1);
      }
      post.reactions[kind] += 1;
      post.reactions.viewer = kind;
    }

    return cloneDiscussion(thread);
  },

  async retractPost(postId: string): Promise<Discussion> {
    const { thread, postIndex } = findPost(postId);
    const post = thread.posts[postIndex];
    if (post === undefined) {
      throw new ApiRequestError('That note could not be found.', 404);
    }
    if (post.author.id !== FIXTURE_VIEWER.id) {
      throw new ApiRequestError('Only the author can retract a note.', 403);
    }

    post.retractedAt = new Date().toISOString();
    post.body = 'This note was retracted.';
    post.capture = null;
    return cloneDiscussion(thread);
  },

  async createCapture(input: CreateCaptureInput): Promise<DashboardCapture> {
    const parsed = CreateCaptureInputSchema.parse(input);
    const capture: DashboardCapture = {
      id: `cap_${crypto.randomUUID()}`,
      altText: parsed.altText,
      imageSrc: parsed.imageSrc,
      filterHash: parsed.filterHash,
      explorerHref: parsed.explorerHref,
    };
    captures.set(capture.id, capture);
    return structuredClone(capture);
  },

  async askAssistant(input: AssistantAskInput): Promise<AssistantReply> {
    const parsed = AssistantAskInputSchema.parse(input);
    const filters = {
      ...(parsed.from === undefined ? {} : { from: parsed.from }),
      ...(parsed.to === undefined ? {} : { to: parsed.to }),
      platforms: parsed.platforms,
      hateTypes: parsed.hateTypes,
      severityBands: parsed.severityBands,
      reviewStates: parsed.reviewStates,
    };
    const [overview, news, page] = await Promise.all([
      fixtureProvider.getOverview(filters),
      fixtureProvider.listNews({
        ...(parsed.from === undefined ? {} : { from: parsed.from }),
        ...(parsed.to === undefined ? {} : { to: parsed.to }),
      }),
      fixtureProvider.searchItems(filters),
    ]);
    return AssistantReplySchema.parse(
      replyFromOverview(parsed.question, overview, {
        news: news.items,
        items: page.items,
      }),
    );
  },

  async prepareReportDraft(input: ReportDraftRequest): Promise<ReportDraft> {
    const parsed = ReportDraftRequestSchema.parse(input);
    return ReportDraftSchema.parse(buildReportDraft(parsed, 'fixture'));
  },

  async listImageExamples(): Promise<ImageExampleList> {
    return ImageExampleListSchema.parse(loadImageExampleList('fixture'));
  },

  async classifyEvidence(input: EvidenceClassifyRequest): Promise<ImageClassification> {
    const parsed = EvidenceClassifyRequestSchema.parse(input);
    return ImageClassificationSchema.parse(
      classifyEvidenceFixture({
        image_filename: parsed.image_filename,
        ...(parsed.example_id === undefined ? {} : { example_id: parsed.example_id }),
      }),
    );
  },
};
