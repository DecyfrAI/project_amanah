import { fixtureProvider } from './fixture-provider';
import { liveProvider } from './live-provider';
import { readDataMode } from './env';
import { ApiRequestError } from './errors';
import type { ApiClient } from './client';

export { FIXTURE_VIEWER, queryKeys } from './client';
export type {
  ApiClient,
  CreateResearchReportInput,
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
  ReportDraft,
  ReportDraftRequest,
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
    classifyEvidence: (input) => tryLive((client) => client.classifyEvidence(input)),
    getCurrentUser: () => tryLive((client) => client.getCurrentUser()),
    updateProfile: (input) => tryLive((client) => client.updateProfile(input)),
    analyzePolicies: (itemId) => tryLive((client) => client.analyzePolicies(itemId)),
    savePreparedReport: (input) => tryLive((client) => client.savePreparedReport(input)),
    recordReportOutcome: (reportId, input) =>
      tryLive((client) => client.recordReportOutcome(reportId, input)),
    listContributions: () => tryLive((client) => client.listContributions()),
    createResearchReport: (input) => tryLive((client) => client.createResearchReport(input)),
    getResearchReport: (reportId) => tryLive((client) => client.getResearchReport(reportId)),
    downloadResearchReportCsv: (reportId) =>
      tryLive((client) => client.downloadResearchReportCsv(reportId)),
  };
}

/**
 * The hackathon demo provider (completion guide, step 2).
 *
 * Every product method routes to the live, authenticated service: news, the
 * dashboard and item reads (including datapack-backed rows), the grounded
 * assistant, insights and discussion, platform and research reports, and the
 * image catalogue/classification. No method here catches a live failure and
 * substitutes fixture data — a failure surfaces to the screen that made the
 * request. The surfaces that remain mocked (the review queue and connections
 * walkthroughs, and the local-file upload rehearsal) do not read through this
 * client at all and are labelled in place.
 */
function createDemoProvider(live: ApiClient): ApiClient {
  return {
    getOverview: live.getOverview,
    getFilterOptions: live.getFilterOptions,
    listNews: live.listNews,
    searchItems: live.searchItems,
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
    classifyEvidence: live.classifyEvidence,
    getCurrentUser: live.getCurrentUser,
    updateProfile: live.updateProfile,
    analyzePolicies: live.analyzePolicies,
    savePreparedReport: live.savePreparedReport,
    recordReportOutcome: live.recordReportOutcome,
    listContributions: live.listContributions,
    createResearchReport: live.createResearchReport,
    getResearchReport: live.getResearchReport,
    downloadResearchReportCsv: live.downloadResearchReportCsv,
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
