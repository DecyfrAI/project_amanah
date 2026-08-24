import { replyFromOverview } from '@/features/ask/ask-reply';
import { readFixtureSession } from '@/features/auth/session';
import { buildResearchReport } from '@/features/reports/build-research-report';
import { validateEvidenceFile } from '@/features/reports/evidence-file';
import { prepareReportDraft as buildReportDraft } from '@/features/reports/prepare-report-draft';
import { renderAggregateCsv } from '@/features/reports/research-report-csv';
import { classifyEvidenceFixture, loadImageExampleList } from './image-classification';

import {
  FIXTURE_VIEWER,
  type ApiClient,
  type ItemSearchFilters,
  type NewsFilters,
  type OverviewFilters,
  type PrepareReportInput,
  type ReportOutcomeInput,
  type UpdateProfileInput,
} from './client';
import type {
  WireContributionsPage,
  WirePolicyAnalysis,
  WirePolicyCandidate,
  WirePreparedReport,
  WireProfile,
} from './wire';
import { itemMatchesQuery } from './item-search';
import {
  AssistantAskInputSchema,
  AssistantReplySchema,
  CreateCaptureInputSchema,
  CreateInsightInputSchema,
  CreatePostInputSchema,
  DiscussionCatalogSchema,
  ExplorerItemDetailSchema,
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
  ImageUploadSchema,
  ReportDraftRequestSchema,
  ReportDraftSchema,
  CreateResearchReportRequestSchema,
  ResearchReportSchema,
  AppendDecisionRequestSchema,
  ReviewDecisionEntrySchema,
  ReviewQueuePageSchema,
  ReviewTaskDetailSchema,
  ReviewTaskSchema,
  ViewerPostListSchema,
  type AssistantAskInput,
  type AssistantReply,
  type CreateCaptureInput,
  type CreateInsightInput,
  type CreatePostInput,
  type DashboardCapture,
  type Discussion,
  type ExplorerItem,
  type ExplorerItemDetail,
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
  type ImageUpload,
  type ReportDraft,
  type ReportDraftRequest,
  type CreateResearchReportRequest,
  type ResearchReport,
  type AppendDecisionRequest,
  type ReviewDecisionEntry,
  type ReviewQueuePage,
  type ReviewTask,
  type ReviewTaskDetail,
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
import reviewTasksJson from '@/fixtures/review-tasks.json' with { type: 'json' };

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

/**
 * What the fixture sample does and does not represent. Mirrors the sentence the
 * live service attaches to every item detail, so the two providers cannot make
 * different claims about the same screen.
 */
const FIXTURE_SAMPLING_DISCLOSURE =
  'These figures describe a monitored sample of reviewed sources, not a platform, a country, or a group of people. They do not support a prevalence claim.';
let discussionCatalog: Discussion[] = [];
const captures = new Map<string, DashboardCapture>();

/**
 * Fixture profile preferences (PA-01). Tab-scoped like the fixture session, so
 * a refresh keeps the choice and closing the tab clears it. The live provider
 * persists the same shape through `PATCH /v1/me`.
 */
const PREFERENCES_KEY = 'amanah.fixture-preferences';

function readFixturePreferences(): Record<string, boolean> {
  try {
    const stored = sessionStorage.getItem(PREFERENCES_KEY);
    if (stored === null) {
      return {};
    }
    const parsed: unknown = JSON.parse(stored);
    if (typeof parsed !== 'object' || parsed === null) {
      return {};
    }
    const preferences: Record<string, boolean> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === 'boolean') {
        preferences[key] = value;
      }
    }
    return preferences;
  } catch {
    return {};
  }
}

let preparedReports: WirePreparedReport[] = [];

/** Same lease window the service uses, so the two behave alike. */
const CLAIM_LEASE_MINUTES = 30;

/**
 * The queue, mutable for the session.
 *
 * Claiming and deciding change state here exactly as they would server-side, so
 * the flow a reviewer practises in fixture mode is the flow they get in live
 * mode. Decisions accumulate; nothing is ever rewritten in place.
 */
const reviewTasks: ReviewTask[] = ReviewTaskSchema.array().parse(reviewTasksJson.items);
const reviewDecisions = new Map<string, ReviewDecisionEntry[]>();
const REVIEW_CLASSIFIED_IN_WINDOW = reviewTasksJson.classified_in_window;

function replaceReviewTask(next: ReviewTask): void {
  const index = reviewTasks.findIndex((task) => task.id === next.id);
  if (index >= 0) {
    reviewTasks[index] = next;
  }
}

/**
 * Queue-wide counts.
 *
 * Derived from the tasks and the decisions actually recorded, so a figure moves
 * when a reviewer decides rather than staying a constant that contradicts the
 * list beneath it.
 */
function reviewTotals(): {
  open: number;
  decided: number;
  confirmed: number;
  classified_in_window: number;
} {
  const appended = [...reviewDecisions.values()].flat();
  return {
    open: reviewTasks.filter((task) => task.status !== 'completed').length,
    decided: reviewTasks.filter((task) => task.status === 'completed').length,
    confirmed: appended.filter((entry) => entry.decision === 'confirmed').length,
    classified_in_window: REVIEW_CLASSIFIED_IN_WINDOW,
  };
}

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

function seedReviewQueue(): void {
  reviewTasks.splice(
    0,
    reviewTasks.length,
    ...ReviewTaskSchema.array().parse(reviewTasksJson.items),
  );
  reviewDecisions.clear();
}

export function resetFixtureProvider(): void {
  seedInsights();
  seedCatalog();
  seedReviewQueue();
  preparedReports = [];
  sessionStorage.removeItem(PREFERENCES_KEY);
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
        // An article whose feed stated no publication time cannot be placed in
        // a calendar window; the retrieval time stands in for ordering only.
        const day = (item.published_at ?? item.retrieved_at).slice(0, 10);
        return day >= window.from && day <= window.to;
      })
      .toSorted((left, right) => {
        const leftAt = left.published_at ?? left.retrieved_at;
        const rightAt = right.published_at ?? right.retrieved_at;
        return leftAt === rightAt ? left.id.localeCompare(right.id) : rightAt.localeCompare(leftAt);
      });

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
  async searchItems(filters: ItemSearchFilters): Promise<ExplorerPage> {
    const applied = appliedFilters(collection, filters);
    const matched = orderedItems.filter(
      (item) => matchesFilters(item, applied) && itemMatchesQuery(item, filters.q),
    );
    const offset = filters.cursor === undefined ? 0 : Number.parseInt(filters.cursor, 10) || 0;
    const page = matched.slice(offset, offset + EXPLORER_PAGE_SIZE);
    const nextOffset = offset + EXPLORER_PAGE_SIZE;

    return ExplorerPageSchema.parse({
      applied,
      matched: matched.length,
      returned: page.length,
      nextCursor: nextOffset < matched.length ? String(nextOffset) : null,
      items: structuredClone(page),
    });
  },

  async getItem(itemId: string): Promise<ExplorerItemDetail> {
    const item = orderedItems.find((entry) => entry.id === itemId);
    if (item === undefined) {
      throw new ApiRequestError('That item could not be found.', 404);
    }
    return ExplorerItemDetailSchema.parse({
      ...structuredClone(item),
      modelName: item.modelScore === null ? null : 'amanah-classifier-fixture',
      modelVersion: item.modelScore === null ? null : 'fixture-0.1',
      promptVersion: item.modelScore === null ? null : 'fixture-prompt-1',
      taxonomyVersion: item.modelScore === null ? null : 'taxonomy-v2-spec-9.5',
      inferredAt: item.modelScore === null ? null : `${item.date}T12:00:00Z`,
      rationale:
        item.modelScore === null
          ? null
          : 'Synthetic fixture rationale. A score is a model score, not a measure of certainty.',
      narrativeTags: [],
      limitations: [
        'This item comes from a monitored sample, not a census of any platform.',
        'A classification is a proposal for human review, never a finding.',
      ],
      samplingDisclosure: FIXTURE_SAMPLING_DISCLOSURE,
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

  async createResearchReport(input: CreateResearchReportRequest): Promise<ResearchReport> {
    const parsed = CreateResearchReportRequestSchema.parse(input);
    // Read the same Overview the reader was looking at, so the snapshot and the
    // dashboard it came from cannot disagree.
    const overview = await fixtureProvider.getOverview({
      ...(parsed.filters.date_from === undefined ? {} : { from: parsed.filters.date_from }),
      ...(parsed.filters.date_to === undefined ? {} : { to: parsed.filters.date_to }),
      platforms: parsed.filters.platforms ?? [],
      hateTypes: [],
      severityBands: parsed.filters.severities ?? [],
      reviewStates: parsed.filters.review_states ?? [],
    });
    return ResearchReportSchema.parse(await buildResearchReport(parsed, overview, 'fixture'));
  },

  async downloadResearchReportCsv(report: ResearchReport): Promise<string> {
    if (!report.aggregate_csv_available) {
      throw new ApiRequestError(
        'Aggregate CSV was not included when this snapshot was generated.',
        409,
      );
    }
    return renderAggregateCsv(report);
  },

  async listReviewTasks(): Promise<ReviewQueuePage> {
    return ReviewQueuePageSchema.parse({
      // Highest priority first, then oldest, matching the server's queue order.
      items: reviewTasks.toSorted((left, right) =>
        left.priority === right.priority
          ? left.created_at.localeCompare(right.created_at)
          : right.priority - left.priority,
      ),
      next_cursor: null,
      totals: reviewTotals(),
    });
  },

  async claimReviewTask(taskId: string): Promise<ReviewTaskDetail> {
    const task = reviewTasks.find((candidate) => candidate.id === taskId);
    if (task === undefined) {
      throw new ApiRequestError('This review task was not found.', 404);
    }
    // A claim is a lease. Re-claiming one you already hold renews it rather than
    // failing, so a reviewer whose page reloaded does not lose their place.
    if (
      task.status === 'claimed' &&
      task.assigned_to !== null &&
      task.assigned_to !== FIXTURE_VIEWER.id
    ) {
      throw new ApiRequestError('Another reviewer is working on this task.', 409);
    }
    if (task.status === 'completed') {
      throw new ApiRequestError('This task has already been decided.', 409);
    }
    const claimed: ReviewTask = {
      ...task,
      status: 'claimed',
      assigned_to: FIXTURE_VIEWER.id,
      claim_expires_at: new Date(Date.now() + CLAIM_LEASE_MINUTES * 60_000).toISOString(),
    };
    replaceReviewTask(claimed);
    return ReviewTaskDetailSchema.parse({
      task: claimed,
      decisions: reviewDecisions.get(taskId) ?? [],
    });
  },

  async appendReviewDecision(
    taskId: string,
    input: AppendDecisionRequest,
  ): Promise<ReviewTaskDetail> {
    const parsed = AppendDecisionRequestSchema.parse(input);
    const task = reviewTasks.find((candidate) => candidate.id === taskId);
    if (task === undefined) {
      throw new ApiRequestError('This review task was not found.', 404);
    }
    if (task.status !== 'claimed' || task.assigned_to !== FIXTURE_VIEWER.id) {
      throw new ApiRequestError('Claim this task before deciding on it.', 409);
    }

    const moment = new Date().toISOString();
    // Decisions append. The prediction on the task is left exactly as it was, so
    // a later reader still sees what the model proposed beside who disagreed.
    const appended = ReviewDecisionEntrySchema.parse({
      id: `rve_${crypto.randomUUID().slice(0, 8)}`,
      review_task_id: taskId,
      reviewer_id: FIXTURE_VIEWER.id,
      decision: parsed.decision,
      corrected_labels: parsed.corrected_labels ?? null,
      note: parsed.note ?? null,
      is_training_candidate: parsed.is_training_candidate,
      created_at: moment,
    });
    reviewDecisions.set(taskId, [...(reviewDecisions.get(taskId) ?? []), appended]);

    // `needs_context` returns the task to the queue; every other decision closes
    // it. The prediction fields are untouched under all of them.
    const settled = parsed.decision !== 'needs_context';
    const next: ReviewTask = {
      ...task,
      status: settled ? 'completed' : 'open',
      assigned_to: settled ? task.assigned_to : null,
      claim_expires_at: null,
      completed_at: settled ? moment : null,
    };
    replaceReviewTask(next);

    return ReviewTaskDetailSchema.parse({
      task: next,
      decisions: reviewDecisions.get(taskId) ?? [],
    });
  },

  async listImageExamples(): Promise<ImageExampleList> {
    return ImageExampleListSchema.parse(loadImageExampleList('fixture'));
  },

  async uploadImage(file: File): Promise<ImageUpload> {
    // The rehearsal path. Nothing leaves the tab: the preview is an object URL,
    // and the identifier is local. Its shape matches the live response so the
    // screens above cannot tell which provider answered.
    const validated = validateEvidenceFile(file);
    return ImageUploadSchema.parse({
      uploadId: `upl_${crypto.randomUUID()}`,
      mimeType: validated.type,
      byteSize: validated.size,
      pixelWidth: 800,
      pixelHeight: 600,
      isNew: true,
      imageSrc: URL.createObjectURL(validated),
      retentionExpiresAt: null,
      disclosure: 'Fixture upload. The file stayed in this tab and no bytes were transmitted.',
    });
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

  async getCurrentUser(): Promise<WireProfile> {
    const session = readFixtureSession();
    return {
      user_id: FIXTURE_VIEWER.id,
      role: 'registered_user',
      display_name: session?.displayName ?? FIXTURE_VIEWER.displayName,
      onboarding_status: 'completed',
      content_safety_preferences: readFixturePreferences(),
    };
  },

  async updateProfile(input: UpdateProfileInput): Promise<WireProfile> {
    if (input.contentSafetyPreferences !== undefined) {
      sessionStorage.setItem(PREFERENCES_KEY, JSON.stringify(input.contentSafetyPreferences));
    }
    const session = readFixtureSession();
    return {
      user_id: FIXTURE_VIEWER.id,
      role: 'registered_user',
      display_name: input.displayName ?? session?.displayName ?? FIXTURE_VIEWER.displayName,
      onboarding_status: input.onboardingStatus ?? 'completed',
      content_safety_preferences: readFixturePreferences(),
    };
  },

  async analyzePolicies(contentItemId: string): Promise<WirePolicyAnalysis> {
    const item = orderedItems.find((entry) => entry.id === contentItemId);
    if (item === undefined) {
      throw new ApiRequestError('This item was not found.', 404);
    }
    if (item.classification !== 'likely_hate') {
      return {
        content_item_id: contentItemId,
        candidates: [],
        matcher_version: 'fixture-matcher-1',
        disclosure:
          'These are possible policy matches, not findings. Read the platform’s own rule and decide for yourself before preparing a report. Amanah never submits one.',
        meta: fixtureMeta(),
      };
    }
    return {
      content_item_id: contentItemId,
      candidates: fixturePolicyCandidates(item.platform),
      matcher_version: 'fixture-matcher-1',
      disclosure:
        'These are possible policy matches, not findings. Read the platform’s own rule and decide for yourself before preparing a report. Amanah never submits one.',
      meta: fixtureMeta(),
    };
  },

  async savePreparedReport(input: PrepareReportInput): Promise<WirePreparedReport> {
    const candidate = FIXTURE_POLICIES.find(
      (policy) => policy.platform_policy_id === input.platformPolicyId,
    );
    if (candidate === undefined) {
      throw new ApiRequestError('That policy is not in the reviewed catalogue.', 422);
    }
    if (candidate.version !== input.policyVersion) {
      throw new ApiRequestError(
        'The policy catalogue changed since you read this rule. Review the current version and confirm it again.',
        409,
      );
    }
    const now = new Date().toISOString();
    const report: WirePreparedReport = {
      id: `rep_${crypto.randomUUID()}`,
      content_item_id: input.contentItemId,
      platform: candidate.platform,
      platform_policy_id: candidate.platform_policy_id,
      policy_version: candidate.version,
      evidence_summary: input.evidenceSummary,
      suggested_text: input.suggestedText,
      status: 'prepared',
      recipient_kind: candidate.recipient_kind,
      recipient_address: candidate.recipient_kind === 'allowlist_email' ? REVIEW_INBOX : null,
      draft_subject: input.draftSubject ?? null,
      submitted_at: null,
      outcome: null,
      outcome_note: null,
      created_at: now,
      updated_at: now,
    };
    preparedReports = [report, ...preparedReports];
    return structuredClone(report);
  },

  async recordReportOutcome(
    reportId: string,
    input: ReportOutcomeInput,
  ): Promise<WirePreparedReport> {
    const report = preparedReports.find((entry) => entry.id === reportId);
    if (report === undefined) {
      throw new ApiRequestError('This prepared report was not found.', 404);
    }
    if (input.status === 'closed' && input.outcome === undefined) {
      throw new ApiRequestError('Closing a report needs the outcome you saw.', 422);
    }
    const now = new Date().toISOString();
    const updated: WirePreparedReport = {
      ...report,
      status: input.status,
      submitted_at: input.status === 'submitted' ? now : report.submitted_at,
      outcome: input.status === 'closed' ? (input.outcome ?? null) : report.outcome,
      outcome_note: input.outcomeNote ?? report.outcome_note,
      updated_at: now,
    };
    preparedReports = preparedReports.map((entry) => (entry.id === reportId ? updated : entry));
    return structuredClone(updated);
  },

  async listContributions(): Promise<WireContributionsPage> {
    return {
      items: preparedReports.map((report) => ({
        id: report.id,
        contribution_type: 'prepared_platform_report' as const,
        label: report.platform,
        status: report.status,
        created_at: report.created_at,
        updated_at: report.updated_at,
        destination_item_id: report.content_item_id,
      })),
      page: { next_cursor: null, limit: 25 },
      meta: fixtureMeta(),
    };
  },
};

const REVIEW_INBOX = 'trust-and-safety-review@amanah.example';

/**
 * The reviewed fixture policy catalogue. Ids and versions are stable so a saved
 * report can be checked against the rule the user confirmed, exactly as the
 * live catalogue does.
 */
const FIXTURE_POLICIES: readonly WirePolicyCandidate[] = [
  {
    platform_policy_id: '4a1f4a1f-0000-4000-8000-000000000001',
    platform: 'youtube',
    policy_key: 'youtube_hate_speech',
    title: 'Hate speech policy',
    summary:
      'Content promoting hatred against individuals or groups based on protected attributes, including religion, is not allowed.',
    official_url: 'https://support.google.com/youtube/answer/2801939',
    version: '2026-05',
    last_reviewed_at: '2026-08-01T00:00:00Z',
    recipient_kind: 'official_form',
    official_report_url: 'https://support.google.com/youtube/answer/2802027',
    score: 0.82,
    confidence_tier: 'high',
    rationale:
      'The classification indicates targeted derogation of a religious group, which this rule covers.',
  },
  {
    platform_policy_id: '4a1f4a1f-0000-4000-8000-000000000002',
    platform: 'youtube',
    policy_key: 'youtube_harassment',
    title: 'Harassment and cyberbullying policy',
    summary: 'Content that threatens individuals or targets someone with prolonged abuse.',
    official_url: 'https://support.google.com/youtube/answer/2802268',
    version: '2026-03',
    last_reviewed_at: '2026-08-01T00:00:00Z',
    recipient_kind: 'official_form',
    official_report_url: 'https://support.google.com/youtube/answer/2802027',
    score: 0.44,
    confidence_tier: 'medium',
    rationale: 'Possible match when the item targets an individual rather than a group.',
  },
  {
    platform_policy_id: '4a1f4a1f-0000-4000-8000-000000000003',
    platform: 'reddit',
    policy_key: 'reddit_rule_1',
    title: 'Rule 1: Remember the human',
    summary:
      'Communities and users that incite violence or promote hate based on identity or vulnerability are banned.',
    official_url: 'https://www.redditinc.com/policies/content-policy',
    version: '2026-01',
    last_reviewed_at: '2026-08-01T00:00:00Z',
    recipient_kind: 'official_form',
    official_report_url: 'https://www.reddit.com/report',
    score: 0.78,
    confidence_tier: 'high',
    rationale: 'The classification indicates identity-based hate, which Rule 1 covers.',
  },
];

function fixturePolicyCandidates(platform: string): WirePolicyCandidate[] {
  const matched = FIXTURE_POLICIES.filter((policy) => policy.platform === platform);
  return structuredClone(
    matched.length > 0 ? matched : [...FIXTURE_POLICIES],
  ) as WirePolicyCandidate[];
}

function fixtureMeta() {
  return {
    request_id: `req_${crypto.randomUUID()}`,
    generated_at: new Date().toISOString(),
    data_mode: 'fixture' as const,
    is_stale: false,
    warnings: [],
  };
}
