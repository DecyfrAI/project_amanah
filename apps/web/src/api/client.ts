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
  ViewerPostList,
} from './contracts';
import type { OverviewFilters } from './fixture-derive';
import type {
  WireContributionsPage,
  WirePolicyAnalysis,
  WirePreparedReport,
  WireProfile,
  WireResearchReport,
} from './wire';

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

/** Cursor-paged item search: the same filters plus an opaque page cursor. */
export interface ItemSearchFilters extends OverviewFilters {
  cursor?: string | undefined;
}

export interface UpdateProfileInput {
  displayName?: string;
  onboardingStatus?: 'not_started' | 'in_progress' | 'completed';
  /** Reveal preferences for redacted text and blurred media (PA-01). */
  contentSafetyPreferences?: Record<string, boolean>;
}

export interface PrepareReportInput {
  contentItemId: string;
  platformPolicyId: string;
  policyVersion: string;
  evidenceSummary: string;
  suggestedText: string;
  /** Only for `allowlist_email` policies (FR-TOS-010); forbidden otherwise. */
  draftSubject?: string;
}

export interface ReportOutcomeInput {
  status: 'submitted' | 'closed';
  outcome?: 'no_response' | 'content_removed' | 'content_restricted' | 'no_violation' | 'other';
  outcomeNote?: string;
}

export interface CreateResearchReportInput {
  title: string;
  filters: OverviewFilters;
  includeAggregateCsv: boolean;
}

export interface ApiClient {
  getOverview: (filters: OverviewFilters) => Promise<Overview>;
  getFilterOptions: () => Promise<FilterOptions>;
  listNews: (filters: NewsFilters) => Promise<NewsList>;
  searchItems: (filters: ItemSearchFilters) => Promise<ExplorerPage>;
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
  listImageExamples: () => Promise<ImageExampleList>;
  classifyEvidence: (input: EvidenceClassifyRequest) => Promise<ImageClassification>;
  getCurrentUser: () => Promise<WireProfile>;
  updateProfile: (input: UpdateProfileInput) => Promise<WireProfile>;
  analyzePolicies: (contentItemId: string) => Promise<WirePolicyAnalysis>;
  savePreparedReport: (input: PrepareReportInput) => Promise<WirePreparedReport>;
  recordReportOutcome: (reportId: string, input: ReportOutcomeInput) => Promise<WirePreparedReport>;
  listContributions: () => Promise<WireContributionsPage>;
  createResearchReport: (input: CreateResearchReportInput) => Promise<WireResearchReport>;
  getResearchReport: (reportId: string) => Promise<WireResearchReport>;
  downloadResearchReportCsv: (reportId: string) => Promise<Blob>;
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
  items: (filters: ItemSearchFilters) =>
    ['items', ...filterKey(filters), filters.cursor ?? null] as const,
  insights: ['insights'] as const,
  insight: (id: string) => ['insights', id] as const,
  viewerPosts: ['viewer-posts'] as const,
  discussion: (insightId: string) => ['discussion', insightId] as const,
  imageExamples: ['image-examples'] as const,
  currentUser: ['current-user'] as const,
  contributions: ['contributions'] as const,
  policyAnalysis: (itemId: string) => ['policy-analysis', itemId] as const,
  researchReport: (reportId: string) => ['research-reports', reportId] as const,
};

export type { OverviewFilters };
