import {
  type ApiClient,
  type CreateResearchReportInput,
  type ItemSearchFilters,
  type NewsFilters,
  type OverviewFilters,
  type PrepareReportInput,
  type ReportOutcomeInput,
  type UpdateProfileInput,
} from './client';
import {
  AssistantAskInputSchema,
  CreateCaptureInputSchema,
  CreateInsightInputSchema,
  CreatePostInputSchema,
  NewsListSchema,
  EvidenceClassifyRequestSchema,
  ReportDraftRequestSchema,
  type AssistantAskInput,
  type AssistantReply,
  type CreateCaptureInput,
  type CreateInsightInput,
  type CreatePostInput,
  type DashboardCapture,
  type Discussion,
  type DiscussionPost,
  type ExplorerItem,
  type ExplorerItemDetail,
  type ExplorerPage,
  type FilterOptions,
  type Insight,
  type InsightList,
  type NewsList,
  type Overview,
  type OverviewDay,
  type OverviewMetric,
  type ReactionKind,
  type EvidenceClassifyRequest,
  type ImageClassification,
  type ImageExampleList,
  type ImageUpload as ImageUploadResult,
  type ReportDraft,
  type ReportDraftRequest,
  type ViewerPostList,
} from './contracts';
import { readApiBaseUrl } from './env';
import { ApiRequestError } from './errors';
import { platformLabel, reviewLabel, severityLabel } from './fixture-derive';
import { endExpiredSession, readAccessToken } from './supabase';
import {
  WireAssistantReplySchema,
  WireCaptureResponseSchema,
  WireContributionsPageSchema,
  WireCurrentUserResponseSchema,
  WireDashboardResponseSchema,
  WireDiscussionResponseSchema,
  WireErrorEnvelopeSchema,
  WireFilterOptionsSchema,
  WireImageClassificationSchema,
  WireImageExampleListSchema,
  WireImageUploadSchema,
  WireInsightResponseSchema,
  WireInsightsPageSchema,
  WireItemDetailResponseSchema,
  WireItemsPageSchema,
  WirePolicyAnalysisSchema,
  WirePostResponseSchema,
  WirePreparedReportResponseSchema,
  WireResearchReportResponseSchema,
  WireViewerPostsPageSchema,
  type WireContributionsPage,
  type WireDashboardResponse,
  type WireDiscussionResponse,
  type WireInsightSummary,
  type WireItemSummary,
  type WirePolicyAnalysis,
  type WirePreparedReport,
  type WireProfile,
  type WireResearchReport,
} from './wire';

/**
 * The live provider: authenticated requests to the deployed FastAPI service.
 *
 * Every request carries the Supabase access token as a bearer header â€” there is
 * no unauthenticated `/v1` route (spec FR-HOME-006). Responses are validated
 * against the backend wire contracts in `wire.ts` and then mapped into the view
 * models the components consume. A failure here surfaces as an
 * `ApiRequestError`; nothing in this module ever substitutes fixture data.
 */

const SESSION_EXPIRED_MESSAGE =
  'Your session has expired or is missing. Sign in again to continue.';
const FORBIDDEN_MESSAGE = 'Your account is not authorized for that action.';

async function readSafeErrorMessage(response: Response): Promise<string | null> {
  try {
    const parsed = WireErrorEnvelopeSchema.safeParse(await response.json());
    return parsed.success ? parsed.data.error.message : null;
  } catch {
    return null;
  }
}

/**
 * Longest a single live request may run before it fails visibly (PA-03). Long
 * enough for the demo host's cold start, bounded so a dead API ends in a
 * retryable error instead of an infinite loading screen.
 */
const REQUEST_TIMEOUT_MS = 60_000;

async function request(path: string, init?: RequestInit): Promise<Response> {
  const token = await readAccessToken();
  // `FormData` sets its own `Content-Type`, including the multipart boundary the
  // server needs to parse the body. Declaring JSON over it would make every
  // upload unreadable.
  const isMultipart = init?.body instanceof FormData;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(init?.body !== undefined && !isMultipart ? { 'Content-Type': 'application/json' } : {}),
    ...(token !== null ? { Authorization: `Bearer ${token}` } : {}),
  };

  let response: Response;
  try {
    response = await fetch(`${readApiBaseUrl()}${path}`, {
      ...init,
      headers,
      signal: init?.signal ?? AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new ApiRequestError(
        'The live service did not answer in time. It may be waking up â€” try again.',
        408,
      );
    }
    throw new ApiRequestError('The live service could not be reached. Try again.', 0);
  }

  if (response.status === 401) {
    // The server rejected the token, so the stored session is spent. Clearing
    // it lets the route guard send the person to sign in again rather than
    // leaving a signed-in-looking shell whose every request fails.
    await endExpiredSession();
    throw new ApiRequestError(SESSION_EXPIRED_MESSAGE, 401);
  }
  if (response.status === 403) {
    // A valid session that lacks permission. The person stays signed in.
    throw new ApiRequestError(FORBIDDEN_MESSAGE, 403);
  }
  if (!response.ok) {
    const message = await readSafeErrorMessage(response);
    throw new ApiRequestError(
      message ?? 'The live service could not complete that request.',
      response.status,
    );
  }
  return response;
}

async function requestJson(path: string, init?: RequestInit): Promise<unknown> {
  const response = await request(path, init);
  return response.json();
}

// -- filter translation -----------------------------------------------------

/** `YYYY-MM-DD` â†’ an aware UTC instant at the start or end of that day. */
function toUtcInstant(date: string, boundary: 'start' | 'end'): string {
  return boundary === 'start' ? `${date}T00:00:00Z` : `${date}T23:59:59Z`;
}

/**
 * Translate view filters into the backend's validated query parameters.
 *
 * The backend rejects unknown parameters rather than widening a query, so only
 * parameters it documents are sent. `hateTypes` and `q` have no server-side
 * filter on `/v1/items` yet (reconciliation G3); they are deliberately not
 * sent, and the `applied` echo the views render reflects what was actually
 * requested rather than pretending the narrowing happened.
 */
function itemQuery(filters: ItemSearchFilters): string {
  const params = new URLSearchParams();
  if (filters.from !== undefined) {
    params.set('date_from', toUtcInstant(filters.from, 'start'));
  }
  if (filters.to !== undefined) {
    params.set('date_to', toUtcInstant(filters.to, 'end'));
  }
  for (const platform of filters.platforms ?? []) {
    params.append('platforms', platform);
  }
  for (const band of filters.severityBands ?? []) {
    params.append('severities', band);
  }
  for (const state of filters.reviewStates ?? []) {
    params.append('review_states', state);
  }
  if (filters.cursor !== undefined) {
    params.set('cursor', filters.cursor);
  }
  const query = params.toString();
  return query === '' ? '' : `?${query}`;
}

function appliedEcho(filters: OverviewFilters, window: { from: string; to: string }) {
  return {
    from: window.from,
    to: window.to,
    platforms: [...(filters.platforms ?? [])],
    // Not supported by the live service; echoed empty so the screen states its
    // real scope instead of a narrowing that did not happen.
    hateTypes: [],
    severityBands: [...(filters.severityBands ?? [])],
    reviewStates: [...(filters.reviewStates ?? [])],
  };
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

// -- dashboard â†’ Overview view model ----------------------------------------

function dateOnly(instant: string): string {
  return instant.slice(0, 10);
}

function overviewMetrics(wire: WireDashboardResponse): OverviewMetric[] {
  const metrics = wire.metrics;
  const rate = metrics.likely_anti_muslim_rate;
  return [
    {
      id: 'observed',
      label: 'Items collected',
      definition:
        'Items successfully collected and stored from the monitored sources in this window. Not a sample of any whole platform.',
      unit: 'count',
      value: metrics.observed_count,
      numerator: null,
      denominator: null,
      isModelOnly: false,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'relevant',
      label: 'Muslim-related items',
      definition:
        'Items the relevance stage judged to be about Muslims or Islam. Relevance is not harm: this count includes neutral and supportive speech.',
      unit: 'count',
      value: metrics.muslim_related_count,
      numerator: metrics.muslim_related_count,
      denominator: metrics.observed_count,
      isModelOnly: true,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'likely-hate',
      label: 'Classified as likely hate',
      definition:
        'Items classified as likely anti-Muslim hate by the model. A classification is a proposal for review, not a finding.',
      unit: 'count',
      value: metrics.likely_anti_muslim_count,
      numerator: metrics.likely_anti_muslim_count,
      denominator: metrics.muslim_related_count,
      isModelOnly: true,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
    {
      id: 'rate',
      label: 'Likely hate rate',
      definition:
        'Items classified as likely anti-Muslim hate, divided by Muslim-related items in the same window and scope.',
      unit: 'rate',
      value: rate.value,
      numerator: rate.numerator,
      denominator: rate.denominator,
      isModelOnly: true,
      insufficientVolume: rate.value === null,
      changeVsBaseline:
        metrics.rate_change === null || rate.value === null
          ? null
          : {
              absolute: metrics.rate_change,
              percent:
                rate.value - metrics.rate_change === 0
                  ? 0
                  : (metrics.rate_change / (rate.value - metrics.rate_change)) * 100,
              baselineLabel: 'preceding window',
            },
    },
    {
      id: 'reviewed',
      label: 'Reviewed by a person',
      definition:
        'Items in this window a trained reviewer has assessed. Every other classification figure is model-only until it appears here.',
      unit: 'count',
      value: metrics.reviewed_count,
      numerator: metrics.reviewed_count,
      denominator: metrics.observed_count,
      isModelOnly: false,
      insufficientVolume: false,
      changeVsBaseline: null,
    },
  ];
}

function overviewDaily(wire: WireDashboardResponse): OverviewDay[] {
  return wire.trend.points.map((point) => {
    if (point.is_gap || point.observed_count === null) {
      return {
        date: dateOnly(point.bucket_start),
        collected: false,
        observed: null,
        relevant: null,
        likelyHate: null,
        nonRelevant: null,
        sources: [],
      };
    }
    const relevant = point.muslim_related_count ?? 0;
    return {
      date: dateOnly(point.bucket_start),
      collected: true,
      observed: point.observed_count,
      relevant,
      likelyHate: point.likely_anti_muslim_count ?? 0,
      nonRelevant: point.observed_count - relevant,
      // The live trend is not broken down per source; an empty stack renders
      // as an unsegmented bar rather than an invented split.
      sources: [],
    };
  });
}

function toOverview(wire: WireDashboardResponse, filters: OverviewFilters): Overview {
  const rate = wire.metrics.likely_anti_muslim_rate;
  const window = {
    from: dateOnly(rate.window_start),
    to: dateOnly(rate.window_end),
    timezone: 'UTC',
  };
  return {
    window,
    coverage: {
      sources: rate.source_scope,
      itemsObserved: wire.metrics.observed_count,
      itemsRelevant: wire.metrics.muslim_related_count,
      lastSuccessfulRun: wire.coverage.last_success_at,
      warnings: [...wire.coverage.warnings, ...wire.meta.warnings],
      containersMonitored: null,
      containerLabel: 'monitored sources',
    },
    applied: appliedEcho(filters, window),
    metrics: overviewMetrics(wire),
    daily: overviewDaily(wire),
    // The live dashboard does not compute composition breakdowns yet
    // (reconciliation G2); an empty list renders as an honest absence.
    breakdowns: [],
  };
}

// -- items â†’ Explorer view model ---------------------------------------------

function toExplorerItem(wire: WireItemSummary): ExplorerItem {
  return {
    id: wire.id,
    date: dateOnly(wire.published_at ?? wire.observed_at),
    platform: wire.platform,
    platformDisplay: wire.platform_display,
    containerTitle: wire.title ?? wire.publisher_or_container,
    containerUrl: wire.canonical_url,
    redactedExcerpt: wire.permitted_excerpt,
    relevance: wire.relevance,
    classification:
      wire.stance === null
        ? null
        : wire.stance === 'likely_anti_muslim'
          ? 'likely_hate'
          : 'not_hate',
    hateType: wire.hate_types[0] ?? null,
    severity: wire.severity,
    modelScore: null,
    reviewState: wire.review_state,
    reviewNote: null,
    isFixture: wire.is_fixture,
    dataset:
      wire.dataset === null || wire.dataset === undefined
        ? null
        : {
            provider: wire.dataset.provider,
            name: wire.dataset.name,
            version: wire.dataset.version,
            licenseId: wire.dataset.license_id,
            landingPageUrl: wire.dataset.landing_page_url,
          },
    image: null,
  };
}

// -- insights â†’ view model ----------------------------------------------------

function toInsight(wire: WireInsightSummary): Insight {
  return {
    id: wire.id,
    title: wire.title,
    summary: wire.claim,
    window: {
      from: dateOnly(wire.window_start),
      to: dateOnly(wire.window_end),
      timezone: 'UTC',
    },
    coverage: {
      sources: wire.source_keys,
      itemsObserved: wire.items_observed,
      itemsRelevant: wire.items_relevant,
      lastSuccessfulRun: null,
      warnings: [],
    },
    facts: [
      {
        id: `fact-${wire.id}`,
        claim: wire.claim,
        numerator: wire.numerator,
        denominator: wire.denominator,
        metric: wire.metric,
      },
    ],
    citations: [
      {
        kind: 'figure',
        id: wire.figure_label,
        label: wire.figure_label,
      },
    ],
    generation: {
      model: wire.author_display_name ?? 'viewer snapshot',
      generatedAt: wire.created_at,
      isMachineGenerated: false,
    },
  };
}

function toDiscussionPost(wire: WireDiscussionResponse['posts'][number]): DiscussionPost {
  return {
    id: wire.id,
    author: {
      id: wire.author_id,
      displayName: wire.author_display_name ?? 'Member',
    },
    body: wire.body,
    createdAt: wire.created_at,
    retractedAt: wire.retracted_at,
    capture:
      wire.capture === null
        ? null
        : {
            id: wire.capture.id,
            altText: wire.capture.alt_text,
            imageSrc: wire.capture.image_source,
            filterHash: wire.capture.filter_hash,
            explorerHref: wire.capture.explorer_href,
          },
    reactions: wire.reactions,
  };
}

function toDiscussion(wire: WireDiscussionResponse): Discussion {
  return {
    insightId: wire.insight_id,
    threadId: wire.insight_id,
    posts: wire.posts.map(toDiscussionPost),
    canParticipate: wire.can_participate,
  };
}

async function fetchDiscussion(insightId: string): Promise<Discussion> {
  return toDiscussion(
    WireDiscussionResponseSchema.parse(await requestJson(`/v1/insights/${insightId}/discussion`)),
  );
}

// -- provider -----------------------------------------------------------------

export const liveProvider: ApiClient = {
  async getOverview(filters: OverviewFilters): Promise<Overview> {
    const wire = WireDashboardResponseSchema.parse(
      await requestJson(`/v1/dashboard${itemQuery(filters)}`),
    );
    return toOverview(wire, filters);
  },

  async getFilterOptions(): Promise<FilterOptions> {
    const wire = WireFilterOptionsSchema.parse(await requestJson('/v1/filters'));
    return {
      // The live service does not report an available-data window; the date
      // picker falls back to an unbounded recent window rather than inventing
      // a range that claims data exists.
      available: null,
      defaultWindowDays: Math.min(30, wire.max_window_days),
      platforms: wire.platforms.map((value) => ({
        value,
        label: platformLabel(value),
        count: null,
      })),
      // `/v1/items` has no hate-type filter yet (reconciliation G3).
      hateTypes: [],
      severityBands: wire.severities.map((value) => ({
        value: String(value),
        label: severityLabel(String(value)),
        count: null,
      })),
      reviewStates: wire.review_states.map((value) => ({
        value,
        label: reviewLabel(value),
        count: null,
      })),
    };
  },

  async listNews(filters: NewsFilters): Promise<NewsList> {
    return NewsListSchema.parse(await requestJson(`/v1/news${newsQuery(filters)}`));
  },

  async searchItems(filters: ItemSearchFilters): Promise<ExplorerPage> {
    const wire = WireItemsPageSchema.parse(await requestJson(`/v1/items${itemQuery(filters)}`));
    const items = wire.items.map(toExplorerItem);
    const dates = items.map((item) => item.date).toSorted();
    return {
      applied: appliedEcho(filters, {
        from: filters.from ?? dates[0] ?? '',
        to: filters.to ?? dates.at(-1) ?? '',
      }),
      matched: null,
      returned: items.length,
      nextCursor: wire.page.next_cursor,
      items,
    };
  },

  async getItem(itemId: string): Promise<ExplorerItemDetail> {
    const wire = WireItemDetailResponseSchema.parse(await requestJson(`/v1/items/${itemId}`));
    const item = wire.item;
    return {
      ...toExplorerItem(item),
      // The summary mapper has no score to read; the detail response does.
      modelScore: item.score,
      modelName: item.model_name,
      modelVersion: item.model_version,
      promptVersion: item.prompt_version,
      taxonomyVersion: item.taxonomy_version,
      inferredAt: item.inferred_at,
      rationale: item.rationale,
      narrativeTags: item.narrative_tags,
      limitations: item.limitations,
      samplingDisclosure: item.sampling_disclosure,
    };
  },

  async listInsights(): Promise<InsightList> {
    const wire = WireInsightsPageSchema.parse(await requestJson('/v1/insights'));
    return { insights: wire.items.map(toInsight) };
  },

  async getInsight(insightId: string): Promise<Insight> {
    const wire = WireInsightResponseSchema.parse(await requestJson(`/v1/insights/${insightId}`));
    return toInsight(wire.insight);
  },

  async createInsight(input: CreateInsightInput): Promise<Insight> {
    const body = CreateInsightInputSchema.parse(input);
    const wire = WireInsightResponseSchema.parse(
      await requestJson('/v1/insights', {
        method: 'POST',
        body: JSON.stringify({
          title: body.title,
          claim: body.claim,
          metric: body.metric,
          numerator: body.numerator,
          denominator: body.denominator,
          window_start: toUtcInstant(body.from, 'start'),
          window_end: toUtcInstant(body.to, 'end'),
          figure_label: body.figureLabel,
          filter_hash: filterHashOf(body.explorerHref),
          explorer_href: body.explorerHref,
          source_keys: body.sources,
          items_observed: body.itemsObserved,
          items_relevant: body.itemsRelevant,
        }),
      }),
    );
    return toInsight(wire.insight);
  },

  async listViewerPosts(): Promise<ViewerPostList> {
    const wire = WireViewerPostsPageSchema.parse(await requestJson('/v1/me/posts'));
    return {
      posts: wire.items.map((post) => {
        const mapped = toDiscussionPost(post);
        return Object.assign(mapped, {
          insightId: post.snapshot_insight_id,
          insightTitle: post.insight_title,
        });
      }),
    };
  },

  async getDiscussion(insightId: string): Promise<Discussion> {
    return fetchDiscussion(insightId);
  },

  async createPost(insightId: string, input: CreatePostInput): Promise<Discussion> {
    const body = CreatePostInputSchema.parse(input);
    WirePostResponseSchema.parse(
      await requestJson(`/v1/insights/${insightId}/discussion/posts`, {
        method: 'POST',
        body: JSON.stringify({
          body: body.body,
          capture_id: body.captureId ?? null,
        }),
      }),
    );
    return fetchDiscussion(insightId);
  },

  async reactToPost(postId: string, kind: ReactionKind): Promise<Discussion> {
    const wire = WirePostResponseSchema.parse(
      await requestJson(`/v1/posts/${postId}/reactions`, {
        method: 'POST',
        body: JSON.stringify({ kind }),
      }),
    );
    return fetchDiscussion(wire.post.snapshot_insight_id);
  },

  async retractPost(postId: string): Promise<Discussion> {
    const wire = WirePostResponseSchema.parse(
      await requestJson(`/v1/posts/${postId}/retract`, { method: 'POST' }),
    );
    return fetchDiscussion(wire.post.snapshot_insight_id);
  },

  async createCapture(input: CreateCaptureInput): Promise<DashboardCapture> {
    const body = CreateCaptureInputSchema.parse(input);
    const wire = WireCaptureResponseSchema.parse(
      await requestJson('/v1/captures', {
        method: 'POST',
        body: JSON.stringify({
          alt_text: body.altText,
          image_source: body.imageSrc,
          filter_hash: body.filterHash,
          explorer_href: body.explorerHref,
        }),
      }),
    );
    return {
      id: wire.capture.id,
      altText: wire.capture.alt_text,
      imageSrc: wire.capture.image_source,
      filterHash: wire.capture.filter_hash,
      explorerHref: wire.capture.explorer_href,
    };
  },

  async askAssistant(input: AssistantAskInput): Promise<AssistantReply> {
    const body = AssistantAskInputSchema.parse(input);
    const filters: Record<string, unknown> = {};
    if (body.from !== undefined) {
      filters.date_from = toUtcInstant(body.from, 'start');
    }
    if (body.to !== undefined) {
      filters.date_to = toUtcInstant(body.to, 'end');
    }
    if (body.platforms !== undefined && body.platforms.length > 0) {
      filters.platforms = body.platforms;
    }
    if (body.severityBands !== undefined && body.severityBands.length > 0) {
      filters.severities = body.severityBands.map((band) => Number(band));
    }
    if (body.reviewStates !== undefined && body.reviewStates.length > 0) {
      filters.review_states = body.reviewStates;
    }
    const wire = WireAssistantReplySchema.parse(
      await requestJson('/v1/assistant/query', {
        method: 'POST',
        body: JSON.stringify({ question: body.question, filters }),
      }),
    );
    return {
      answer: wire.answer,
      citations: wire.citations,
      limitations: wire.limitations,
      groundedIn: wire.grounded_in,
    };
  },

  async prepareReportDraft(input: ReportDraftRequest): Promise<ReportDraft> {
    ReportDraftRequestSchema.parse(input);
    // The live path is the policy-catalog flow (analyzePolicies â†’
    // savePreparedReport). The freeform email-style draft remains a declared
    // fixture rehearsal, so this surface is hidden outside fixture mode.
    throw new ApiRequestError(
      'The live service prepares reports through the policy-catalog flow. Select an item and analyse its policies instead.',
      501,
    );
  },

  async listImageExamples(): Promise<ImageExampleList> {
    const wire = WireImageExampleListSchema.parse(await requestJson('/v1/image-examples'));
    return {
      data_mode: wire.data_mode,
      manifest: wire.manifest,
      items: wire.items.map((entry) => ({
        id: entry.id,
        title: entry.title,
        image_src: entry.image_url,
        alt_text: entry.alt_text,
        form_note: entry.form_note,
        dataset_annotation: entry.dataset_annotation,
        score: entry.score,
        narrative_tags: entry.narrative_tags,
        rationale: entry.rationale,
      })),
    };
  },

  async uploadImage(file: File): Promise<ImageUploadResult> {
    // `FormData` rather than JSON: the bytes go to the backend, which cleans and
    // stores them. The browser never talks to object storage directly, and it
    // never sends base64 (ADR 0007, B-S28).
    const form = new FormData();
    form.append('file', file, file.name);
    const wire = WireImageUploadSchema.parse(
      await requestJson('/v1/image-uploads', { method: 'POST', body: form }),
    );
    return {
      uploadId: wire.upload_id,
      mimeType: wire.mime_type,
      byteSize: wire.byte_size,
      pixelWidth: wire.pixel_width,
      pixelHeight: wire.pixel_height,
      isNew: wire.is_new,
      imageSrc: wire.image_url,
      retentionExpiresAt: wire.retention_expires_at,
      disclosure: wire.disclosure,
    };
  },

  async classifyEvidence(input: EvidenceClassifyRequest): Promise<ImageClassification> {
    const body = EvidenceClassifyRequestSchema.parse(input);
    if (body.example_id === undefined && body.upload_id === undefined) {
      // The service classifies something already stored. A caller that named
      // neither has not uploaded yet, and inventing a subject would produce a
      // label about nothing.
      throw new ApiRequestError('Upload the image first, then ask for a classification.', 400);
    }
    const subject =
      body.upload_id !== undefined
        ? { upload_id: body.upload_id }
        : { example_id: body.example_id };
    const wire = WireImageClassificationSchema.parse(
      await requestJson('/v1/image-classifications', {
        method: 'POST',
        body: JSON.stringify(subject),
      }),
    );
    return {
      data_mode: wire.data_mode,
      example_id: wire.example_id ?? wire.upload_id ?? '',
      relevance: wire.relevance,
      stance: wire.stance,
      classification: wire.stance === 'likely_anti_muslim' ? 'likely_hate' : 'not_hate',
      hate_types: wire.hate_types,
      severity: wire.severity,
      narrative_tags: wire.narrative_tags,
      score: wire.score,
      confidence_tier: wire.confidence_tier,
      rationale: wire.rationale,
      model_name: wire.model_name,
      model_version: wire.model_version,
      taxonomy_version: wire.taxonomy_version,
      review_required: wire.review_required,
      dataset_annotation: wire.dataset_annotation,
      status: 'classified_not_reviewed',
      disclosure: wire.disclosure,
    };
  },

  async getCurrentUser(): Promise<WireProfile> {
    const wire = WireCurrentUserResponseSchema.parse(await requestJson('/v1/me'));
    return wire.profile;
  },

  async updateProfile(input: UpdateProfileInput): Promise<WireProfile> {
    const body: Record<string, unknown> = {};
    if (input.displayName !== undefined) {
      body.display_name = input.displayName;
    }
    if (input.onboardingStatus !== undefined) {
      body.onboarding_status = input.onboardingStatus;
    }
    if (input.contentSafetyPreferences !== undefined) {
      body.content_safety_preferences = input.contentSafetyPreferences;
    }
    const wire = WireCurrentUserResponseSchema.parse(
      await requestJson('/v1/me', { method: 'PATCH', body: JSON.stringify(body) }),
    );
    return wire.profile;
  },

  async analyzePolicies(contentItemId: string): Promise<WirePolicyAnalysis> {
    return WirePolicyAnalysisSchema.parse(
      await requestJson(`/v1/items/${contentItemId}/policy-analysis`, { method: 'POST' }),
    );
  },

  async savePreparedReport(input: PrepareReportInput): Promise<WirePreparedReport> {
    const wire = WirePreparedReportResponseSchema.parse(
      await requestJson('/v1/prepared-reports', {
        method: 'POST',
        body: JSON.stringify({
          content_item_id: input.contentItemId,
          platform_policy_id: input.platformPolicyId,
          policy_version: input.policyVersion,
          evidence_summary: input.evidenceSummary,
          suggested_text: input.suggestedText,
          draft_subject: input.draftSubject ?? null,
        }),
      }),
    );
    return wire.report;
  },

  async recordReportOutcome(
    reportId: string,
    input: ReportOutcomeInput,
  ): Promise<WirePreparedReport> {
    const wire = WirePreparedReportResponseSchema.parse(
      await requestJson(`/v1/prepared-reports/${reportId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: input.status,
          outcome: input.outcome ?? null,
          outcome_note: input.outcomeNote ?? null,
        }),
      }),
    );
    return wire.report;
  },

  async listContributions(): Promise<WireContributionsPage> {
    return WireContributionsPageSchema.parse(await requestJson('/v1/me/contributions'));
  },

  async createResearchReport(input: CreateResearchReportInput): Promise<WireResearchReport> {
    const filters: Record<string, unknown> = {};
    if (input.filters.from !== undefined) {
      filters.date_from = toUtcInstant(input.filters.from, 'start');
    }
    if (input.filters.to !== undefined) {
      filters.date_to = toUtcInstant(input.filters.to, 'end');
    }
    if (input.filters.platforms !== undefined && input.filters.platforms.length > 0) {
      filters.platforms = input.filters.platforms;
    }
    if (input.filters.severityBands !== undefined && input.filters.severityBands.length > 0) {
      filters.severities = input.filters.severityBands.map((band) => Number(band));
    }
    if (input.filters.reviewStates !== undefined && input.filters.reviewStates.length > 0) {
      filters.review_states = input.filters.reviewStates;
    }
    const wire = WireResearchReportResponseSchema.parse(
      await requestJson('/v1/research-reports', {
        method: 'POST',
        body: JSON.stringify({
          title: input.title,
          filters,
          include_aggregate_csv: input.includeAggregateCsv,
        }),
      }),
    );
    return wire.report;
  },

  async getResearchReport(reportId: string): Promise<WireResearchReport> {
    const wire = WireResearchReportResponseSchema.parse(
      await requestJson(`/v1/research-reports/${reportId}`),
    );
    return wire.report;
  },

  async downloadResearchReportCsv(reportId: string): Promise<Blob> {
    const response = await request(`/v1/research-reports/${reportId}/summary.csv`);
    return response.blob();
  },
};

/**
 * A stable hex digest of the Explorer state a figure was read under.
 *
 * The backend requires an 8â€“64 char hex `filter_hash`; the view layer carries
 * the href itself. FNV-1a over the href is enough: this identifies a filter
 * state, it is not a security control.
 */
function filterHashOf(href: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < href.length; index += 1) {
    hash ^= href.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}
