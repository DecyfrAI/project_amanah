import { fixtureProvider } from './fixture-provider';
import { liveProvider } from './live-provider';
import { readDataMode } from './env';
import { ApiRequestError } from './errors';
import type { ApiClient } from './client';

export { FIXTURE_VIEWER, queryKeys } from './client';
export type { ApiClient, NewsFilters, OverviewFilters } from './client';
export type {
  AppliedFilters,
  AssistantAskInput,
  AssistantReply,
  BreakdownRow,
  CreateInsightInput,
  ExplorerItem,
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
export { hateTypeLabel, platformLabel, reviewLabel, severityLabel } from './fixture-derive';
export { ApiRequestError } from './errors';
export { isFixtureVisible, readDataMode } from './env';
export type { DataMode } from './env';

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
  };
}

export function createApiClient(): ApiClient {
  const mode = readDataMode();
  if (mode === 'live') {
    return liveProvider;
  }
  if (mode === 'fallback') {
    return withFallback(liveProvider, fixtureProvider);
  }
  return fixtureProvider;
}

export const apiClient = createApiClient();
