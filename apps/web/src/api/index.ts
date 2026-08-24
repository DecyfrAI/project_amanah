import { fixtureProvider } from './fixture-provider';
import { liveProvider } from './live-provider';
import { readDataMode } from './env';
import { ApiRequestError } from './errors';
import type { ApiClient } from './client';

export { FIXTURE_VIEWER, queryKeys } from './client';
export type {
  ApiClient,
  ItemSearchFilters,
  NewsFilters,
  OverviewFilters,
  PrepareReportInput,
  ReportOutcomeInput,
  UpdateProfileInput,
} from './client';
export type {
  AppliedFilters,
  AssistantAskInput,
  AssistantReply,
  BreakdownRow,
  CreateInsightInput,
  ExplorerItem,
  ExplorerItemDataset,
  ExplorerItemDetail,
  ExplorerItemImage,
  ExplorerPage,
  FilterOption,
  FilterOptions,
  Insight,
  NewsItem,
  NewsList,
  Overview,
  OverviewBreakdown,
  OverviewDay,
  OverviewMetric,
  EvidenceClassifyRequest,
  HateType,
  ImageClassification,
  ImageExample,
  ImageExampleList,
  ImageUpload,
  ReportDraft,
  ReportDraftRequest,
  CreateResearchReportRequest,
  ReportFindingSnapshot,
  ReportMetricKey,
  ReportMetricSnapshot,
  ResearchReport,
  ReviewTaskType,
  Relevance,
  // The review queue reads these through the same barrel as every other
  // feature; they were defined in `contracts.ts` but never re-exported here.
  AppendDecisionRequest,
  ReviewDecisionEntry,
  ReviewDecisionKind,
  ReviewQueuePage,
  ReviewTask,
  ReviewTaskDetail,
  Stance,
  ViewerPost,
  ViewerPostList,
} from './contracts';
export type {
  WireContributionsPage,
  WireContributionSummary,
  WirePolicyAnalysis,
  WirePolicyCandidate,
  WirePreparedReport,
  WireProfile,
  WireResearchReport,
} from './wire';
export { hateTypeLabel, platformLabel, reviewLabel, severityLabel } from './fixture-derive';
export { ApiRequestError } from './errors';
export { isFixtureVisible, readDataMode, usesLiveAuthentication } from './env';
export type { DataMode } from './env';
export { isSupabaseConfigured } from './supabase';

let fallbackActive = false;

export function isFallbackActive(): boolean {
  return fallbackActive;
}

function withFallback(live: ApiClient, fixture: ApiClient): ApiClient {
  async function tryLive<T>(operation: (client: ApiClient) => Promise<T>): Promise<T> {
    try {
      const result = await operation(live);
      fallbackActive = false;
      return result;
    } catch (error) {
      fallbackActive = true;
      if (error instanceof ApiRequestError || error instanceof Error) {
        return operation(fixture);
      }
      return operation(fixture);
    }
  }

  return {
    getOverview: (filters) => tryLive((client) => client.getOverview(filters)),
    getFilterOptions: () => tryLive((client) => client.getFilterOptions()),
    listNews: (filters) => tryLive((client) => client.listNews(filters)),
    searchItems: (filters) => tryLive((client) => client.searchItems(filters)),
    getItem: (itemId) => tryLive((client) => client.getItem(itemId)),
    listInsights: () => tryLive((client) => client.listInsights()),
    getInsight: (insightId) => tryLive((client) => client.getInsight(insightId)),
    createInsight: (input) => tryLive((client) => client.createInsight(input)),
    listViewerPosts: () => tryLive((client) => client.listViewerPosts()),
    getDiscussion: (insightId) => tryLive((client) => client.getDiscussion(insightId)),
    createPost: (insightId, input) => tryLive((client) => client.createPost(insightId, input)),
    reactToPost: (postId, kind) => tryLive((client) => client.reactToPost(postId, kind)),
    retractPost: (postId) => tryLive((client) => client.retractPost(postId)),
    createCapture: (input) => tryLive((client) => client.createCapture(input)),
    askAssistant: (input) => tryLive((client) => client.askAssistant(input)),
    prepareReportDraft: (input) => tryLive((client) => client.prepareReportDraft(input)),
    listImageExamples: () => tryLive((client) => client.listImageExamples()),
    uploadImage: (file) => tryLive((client) => client.uploadImage(file)),
    classifyEvidence: (input) => tryLive((client) => client.classifyEvidence(input)),
    getCurrentUser: () => tryLive((client) => client.getCurrentUser()),
    updateProfile: (input) => tryLive((client) => client.updateProfile(input)),
    analyzePolicies: (itemId) => tryLive((client) => client.analyzePolicies(itemId)),
    savePreparedReport: (input) => tryLive((client) => client.savePreparedReport(input)),
    recordReportOutcome: (reportId, input) =>
      tryLive((client) => client.recordReportOutcome(reportId, input)),
    listContributions: () => tryLive((client) => client.listContributions()),
    createResearchReport: (input) => tryLive((client) => client.createResearchReport(input)),
    downloadResearchReportCsv: (report) =>
      tryLive((client) => client.downloadResearchReportCsv(report)),
    listReviewTasks: () => tryLive((client) => client.listReviewTasks()),
    claimReviewTask: (taskId) => tryLive((client) => client.claimReviewTask(taskId)),
    appendReviewDecision: (taskId, input) =>
      tryLive((client) => client.appendReviewDecision(taskId, input)),
  };
}

/**
 * The hackathon demo provider (completion guide, step 2).
 *
 * Every product method routes to the live, authenticated service: news, the
 * dashboard and item reads (including datapack-backed rows), the grounded
 * assistant, insights and discussion, platform and research reports, and the
 * image catalogue/classification, and the review queue. No method here catches
 * a live failure and substitutes fixture data — a failure surfaces to the screen that made the
 * request. The surfaces that remain mocked (the connections walkthrough and
 * the local-file upload rehearsal) do not read through this client at all and
 * are labelled in place.
 */
function createDemoProvider(live: ApiClient): ApiClient {
  return {
    getOverview: live.getOverview,
    getFilterOptions: live.getFilterOptions,
    listNews: live.listNews,
    searchItems: live.searchItems,
    getItem: live.getItem,
    listInsights: live.listInsights,
    getInsight: live.getInsight,
    createInsight: live.createInsight,
    listViewerPosts: live.listViewerPosts,
    getDiscussion: live.getDiscussion,
    createPost: live.createPost,
    reactToPost: live.reactToPost,
    retractPost: live.retractPost,
    createCapture: live.createCapture,
    askAssistant: live.askAssistant,
    prepareReportDraft: live.prepareReportDraft,
    listImageExamples: live.listImageExamples,
    uploadImage: live.uploadImage,
    classifyEvidence: live.classifyEvidence,
    getCurrentUser: live.getCurrentUser,
    updateProfile: live.updateProfile,
    analyzePolicies: live.analyzePolicies,
    savePreparedReport: live.savePreparedReport,
    recordReportOutcome: live.recordReportOutcome,
    listContributions: live.listContributions,
    createResearchReport: live.createResearchReport,
    downloadResearchReportCsv: live.downloadResearchReportCsv,
    listReviewTasks: live.listReviewTasks,
    claimReviewTask: live.claimReviewTask,
    appendReviewDecision: live.appendReviewDecision,
  };
}

export function createApiClient(): ApiClient {
  const mode = readDataMode();
  if (mode === 'live') {
    return liveProvider;
  }
  if (mode === 'demo') {
    return createDemoProvider(liveProvider);
  }
  if (mode === 'fallback') {
    return withFallback(liveProvider, fixtureProvider);
  }
  return fixtureProvider;
}

export const apiClient = createApiClient();
