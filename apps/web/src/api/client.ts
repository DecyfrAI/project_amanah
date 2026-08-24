import type {
  AssistantAskInput,
  AssistantReply,
  CreateCaptureInput,
  CreateInsightInput,
  CreatePostInput,
  DashboardCapture,
  Discussion,
  ExplorerPage,
  FilterOptions,
  Insight,
  InsightList,
  NewsList,
  Overview,
  ReactionKind,
  EvidenceClassifyRequest,
  ImageClassification,
  ImageExampleList,
  ReportDraft,
  ReportDraftRequest,
  CreateResearchReportRequest,
  ResearchReport,
  ViewerPostList,
} from './contracts';
import type { OverviewFilters } from './fixture-derive';

/**
 * The single data-access surface. Views never call fetch or read a fixture.
 *
 * Two implementations sit behind this: the fixture provider and the live
 * provider. Adding an endpoint means adding it here first, then to both
 * implementations and to the Zod contract.
 */
export interface NewsFilters {
  from?: string | undefined;
  to?: string | undefined;
  cursor?: string | undefined;
}

export interface ApiClient {
  getOverview: (filters: OverviewFilters) => Promise<Overview>;
  getFilterOptions: () => Promise<FilterOptions>;
  listNews: (filters: NewsFilters) => Promise<NewsList>;
  searchItems: (filters: OverviewFilters) => Promise<ExplorerPage>;
  listInsights: () => Promise<InsightList>;
  getInsight: (insightId: string) => Promise<Insight>;
  createInsight: (input: CreateInsightInput) => Promise<Insight>;
  listViewerPosts: () => Promise<ViewerPostList>;
  getDiscussion: (insightId: string) => Promise<Discussion>;
  createPost: (insightId: string, input: CreatePostInput) => Promise<Discussion>;
  reactToPost: (postId: string, kind: ReactionKind) => Promise<Discussion>;
  retractPost: (postId: string) => Promise<Discussion>;
  createCapture: (input: CreateCaptureInput) => Promise<DashboardCapture>;
  askAssistant: (input: AssistantAskInput) => Promise<AssistantReply>;
  prepareReportDraft: (input: ReportDraftRequest) => Promise<ReportDraft>;
  createResearchReport: (input: CreateResearchReportRequest) => Promise<ResearchReport>;
  /** The frozen aggregate CSV as text, ready to hand to a download. */
  downloadResearchReportCsv: (report: ResearchReport) => Promise<string>;
  listImageExamples: () => Promise<ImageExampleList>;
  classifyEvidence: (input: EvidenceClassifyRequest) => Promise<ImageClassification>;
}

export const FIXTURE_VIEWER: { id: string; displayName: string } = {
  id: 'user_demo',
  displayName: 'Demo reviewer',
};

function filterKey(filters: OverviewFilters): readonly (string | null)[] {
  return [
    filters.from ?? null,
    filters.to ?? null,
    (filters.platforms ?? []).toSorted().join(',') || null,
    (filters.hateTypes ?? []).toSorted().join(',') || null,
    (filters.severityBands ?? []).toSorted().join(',') || null,
    (filters.reviewStates ?? []).toSorted().join(',') || null,
    filters.q?.trim() || null,
  ];
}

export const queryKeys = {
  /**
   * Every filter is part of the key, so changing one invalidates the cache
   * automatically instead of leaving a stale reading under a new window. Multi
   * value filters are sorted first, since two orderings of the same selection
   * describe the same request and should share one cache entry.
   */
  overview: (filters: OverviewFilters) => ['overview', ...filterKey(filters)] as const,
  filterOptions: ['filter-options'] as const,
  /**
   * Window only. Platform and taxonomy filters do not apply to published
   * news, which is coinciding context rather than a classified item.
   */
  news: (filters: NewsFilters) =>
    ['news', filters.from ?? null, filters.to ?? null, filters.cursor ?? null] as const,
  items: (filters: OverviewFilters) => ['items', ...filterKey(filters)] as const,
  insights: ['insights'] as const,
  insight: (id: string) => ['insights', id] as const,
  viewerPosts: ['viewer-posts'] as const,
  discussion: (insightId: string) => ['discussion', insightId] as const,
  imageExamples: ['image-examples'] as const,
};

export type { OverviewFilters };
