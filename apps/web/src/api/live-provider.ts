import { type ApiClient, type NewsFilters, type OverviewFilters } from './client';
import {
  AssistantAskInputSchema,
  AssistantReplySchema,
  CreateCaptureInputSchema,
  CreateInsightInputSchema,
  CreatePostInputSchema,
  DashboardCaptureSchema,
  DiscussionSchema,
  ExplorerPageSchema,
  FilterOptionsSchema,
  InsightListSchema,
  InsightSchema,
  NewsListSchema,
  OverviewSchema,
  EvidenceClassifyRequestSchema,
  ReportDraftRequestSchema,
  CreateResearchReportRequestSchema,
  ResearchReportSchema,
  AppendDecisionRequestSchema,
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
  type ExplorerPage,
  type FilterOptions,
  type Insight,
  type InsightList,
  type NewsList,
  type Overview,
  type ReactionKind,
  type EvidenceClassifyRequest,
  type ImageClassification,
  type ImageExampleList,
  type ReportDraft,
  type ReportDraftRequest,
  type CreateResearchReportRequest,
  type ResearchReport,
  type AppendDecisionRequest,
  type ReviewQueuePage,
  type ReviewTaskDetail,
  type ViewerPostList,
} from './contracts';
import { readApiBaseUrl } from './env';
import { ApiRequestError } from './errors';

async function requestJson(path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${readApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiRequestError('The live service could not complete that request.', response.status);
  }

  return response.json();
}

/**
 * Query string for a filtered request.
 *
 * Fields are `snake_case` and multi-value filters repeat the key, which is what
 * the API contract in AGENTS.md specifies. Nothing is dropped silently: an
 * unsupported value is the service's error to raise, not ours to swallow.
 */
function overviewQuery(filters: OverviewFilters): string {
  const params = new URLSearchParams();
  if (filters.from !== undefined) {
    params.set('from', filters.from);
  }
  if (filters.to !== undefined) {
    params.set('to', filters.to);
  }
  for (const platform of filters.platforms ?? []) {
    params.append('platform', platform);
  }
  for (const type of filters.hateTypes ?? []) {
    params.append('hate_type', type);
  }
  for (const band of filters.severityBands ?? []) {
    params.append('severity', band);
  }
  for (const state of filters.reviewStates ?? []) {
    params.append('review_state', state);
  }
  if (filters.q !== undefined && filters.q.trim() !== '') {
    params.set('q', filters.q.trim());
  }
  const query = params.toString();
  return query === '' ? '' : `?${query}`;
}

function newsQuery(filters: NewsFilters): string {
  const params = new URLSearchParams();
  if (filters.from !== undefined) {
    params.set('from', filters.from);
  }
  if (filters.to !== undefined) {
    params.set('to', filters.to);
  }
  if (filters.cursor !== undefined) {
    params.set('cursor', filters.cursor);
  }
  const query = params.toString();
  return query === '' ? '' : `?${query}`;
}

export const liveProvider: ApiClient = {
  async getOverview(filters: OverviewFilters): Promise<Overview> {
    return OverviewSchema.parse(await requestJson(`/v1/overview${overviewQuery(filters)}`));
  },

  async getFilterOptions(): Promise<FilterOptions> {
    return FilterOptionsSchema.parse(await requestJson('/v1/filters'));
  },

  async listNews(filters: NewsFilters): Promise<NewsList> {
    return NewsListSchema.parse(await requestJson(`/v1/news${newsQuery(filters)}`));
  },

  async searchItems(filters: OverviewFilters): Promise<ExplorerPage> {
    return ExplorerPageSchema.parse(await requestJson(`/v1/items${overviewQuery(filters)}`));
  },

  async listInsights(): Promise<InsightList> {
    return InsightListSchema.parse(await requestJson('/v1/insights'));
  },

  async getInsight(insightId: string): Promise<Insight> {
    return InsightSchema.parse(await requestJson(`/v1/insights/${insightId}`));
  },

  async createInsight(input: CreateInsightInput): Promise<Insight> {
    const body = CreateInsightInputSchema.parse(input);
    return InsightSchema.parse(
      await requestJson('/v1/insights', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    );
  },

  async listViewerPosts(): Promise<ViewerPostList> {
    return ViewerPostListSchema.parse(await requestJson('/v1/me/posts'));
  },

  async getDiscussion(insightId: string): Promise<Discussion> {
    return DiscussionSchema.parse(await requestJson(`/v1/insights/${insightId}/discussion`));
  },

  async createPost(insightId: string, input: CreatePostInput): Promise<Discussion> {
    const body = CreatePostInputSchema.parse(input);
    return DiscussionSchema.parse(
      await requestJson(`/v1/insights/${insightId}/discussion/posts`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    );
  },

  async reactToPost(postId: string, kind: ReactionKind): Promise<Discussion> {
    return DiscussionSchema.parse(
      await requestJson(`/v1/posts/${postId}/reactions`, {
        method: 'POST',
        body: JSON.stringify({ kind }),
      }),
    );
  },

  async retractPost(postId: string): Promise<Discussion> {
    return DiscussionSchema.parse(
      await requestJson(`/v1/posts/${postId}/retract`, {
        method: 'POST',
      }),
    );
  },

  async createCapture(input: CreateCaptureInput): Promise<DashboardCapture> {
    const body = CreateCaptureInputSchema.parse(input);
    return DashboardCaptureSchema.parse(
      await requestJson('/v1/captures', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    );
  },

  async askAssistant(input: AssistantAskInput): Promise<AssistantReply> {
    const body = AssistantAskInputSchema.parse(input);
    return AssistantReplySchema.parse(
      await requestJson('/v1/assistant/query', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    );
  },

  async prepareReportDraft(input: ReportDraftRequest): Promise<ReportDraft> {
    ReportDraftRequestSchema.parse(input);
    throw new ApiRequestError(
      'The live service cannot prepare a report draft yet. Platform addresses come from a backend allow-list that is not connected. Use fixture mode to practise this flow.',
      501,
    );
  },

  /**
   * Freeze a snapshot server-side. The response carries the report nested under
   * `report`, alongside the standard response meta.
   */
  async createResearchReport(input: CreateResearchReportRequest): Promise<ResearchReport> {
    const body = CreateResearchReportRequestSchema.parse(input);
    const payload = await requestJson('/v1/research-reports', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return ResearchReportSchema.parse((payload as { report: unknown }).report);
  },

  /**
   * Fetch the server's own CSV rendering rather than re-deriving it here, so the
   * bytes a reader receives are the ones the service audited handing out.
   */
  async downloadResearchReportCsv(report: ResearchReport): Promise<string> {
    const response = await fetch(
      `${readApiBaseUrl()}/v1/research-reports/${report.id}/summary.csv`,
      { headers: { Accept: 'text/csv' } },
    );
    if (!response.ok) {
      throw new ApiRequestError(
        response.status === 409
          ? 'Aggregate CSV was not included when this snapshot was generated.'
          : 'The live service could not produce the aggregate CSV.',
        response.status,
      );
    }
    return response.text();
  },

  /**
   * The reviewer queue.
   *
   * The service returns a cursor page of tasks and no queue-wide totals, so the
   * counts are derived from the page rather than invented. `classified_in_window`
   * has no live source yet and is reported as zero, which the queue reads as
   * "unknown" rather than as a real denominator.
   */
  async listReviewTasks(): Promise<ReviewQueuePage> {
    const payload = (await requestJson('/v1/review/tasks')) as {
      items: unknown[];
      page: { next_cursor: string | null };
    };
    const items = ReviewTaskSchema.array().parse(payload.items);
    return ReviewQueuePageSchema.parse({
      items,
      next_cursor: payload.page.next_cursor,
      totals: {
        open: items.filter((task) => task.status !== 'completed').length,
        decided: items.filter((task) => task.status === 'completed').length,
        confirmed: 0,
        classified_in_window: 0,
      },
    });
  },

  async claimReviewTask(taskId: string): Promise<ReviewTaskDetail> {
    const payload = await requestJson(`/v1/review/tasks/${taskId}/claim`, { method: 'POST' });
    return ReviewTaskDetailSchema.parse(payload);
  },

  /**
   * Append a decision, then re-read the task so the caller receives the full
   * decision history rather than only the row just written.
   */
  async appendReviewDecision(
    taskId: string,
    input: AppendDecisionRequest,
  ): Promise<ReviewTaskDetail> {
    const body = AppendDecisionRequestSchema.parse(input);
    await requestJson(`/v1/review/tasks/${taskId}/decisions`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return ReviewTaskDetailSchema.parse(await requestJson(`/v1/review/tasks/${taskId}`));
  },

  async listImageExamples(): Promise<ImageExampleList> {
    throw new ApiRequestError(
      'The live service cannot list image examples yet. Use fixture mode to read the research catalog.',
      501,
    );
  },

  async classifyEvidence(input: EvidenceClassifyRequest): Promise<ImageClassification> {
    EvidenceClassifyRequestSchema.parse(input);
    throw new ApiRequestError(
      'The live service cannot classify an image yet. Classification runs behind FastAPI after an object-storage upload. Use fixture mode to practise this flow.',
      501,
    );
  },
};
