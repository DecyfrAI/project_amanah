import { z } from 'zod';

/**
 * The backend's own `/v1` response shapes, exactly as FastAPI serializes them.
 *
 * These schemas mirror `backend/src/amanah/api/schemas/*` — the OpenAPI/Pydantic
 * contracts are the service-boundary source of truth (AGENTS.md), so live
 * responses are validated against *these* and then mapped into the view models
 * in `contracts.ts`. Field names stay `snake_case` because that is what crosses
 * the wire; nothing here is reshaped before validation.
 *
 * `z.object` ignores unknown keys, so an additive backend field does not break
 * a deployed frontend. A removed or renamed field still fails loudly.
 */

export const WireDataModeSchema = z.enum(['fixture', 'live', 'fallback']);

export const WireMetaSchema = z.object({
  request_id: z.string(),
  generated_at: z.string(),
  data_mode: WireDataModeSchema,
  is_stale: z.boolean(),
  warnings: z.array(z.string()),
});

export const WireCoverageSummarySchema = z.object({
  last_success_at: z.string().nullable(),
  coverage_score: z.number().min(0).max(1).nullable(),
  data_mode: WireDataModeSchema,
  is_stale: z.boolean(),
  warnings: z.array(z.string()),
});

export const WireMetricRateSchema = z.object({
  numerator: z.number().int().nonnegative(),
  denominator: z.number().int().nonnegative(),
  window_start: z.string(),
  window_end: z.string(),
  source_scope: z.array(z.string()),
  coverage_score: z.number().min(0).max(1).nullable(),
  data_mode: WireDataModeSchema,
  value: z.number().nullable(),
});

export const WireDashboardMetricsSchema = z.object({
  observed_count: z.number().int().nonnegative(),
  muslim_related_count: z.number().int().nonnegative(),
  likely_anti_muslim_count: z.number().int().nonnegative(),
  reviewed_count: z.number().int().nonnegative(),
  likely_anti_muslim_rate: WireMetricRateSchema,
  rate_change: z.number().nullable(),
});

export const WireTrendPointSchema = z.object({
  bucket_start: z.string(),
  is_gap: z.boolean(),
  observed_count: z.number().int().nonnegative().nullable(),
  muslim_related_count: z.number().int().nonnegative().nullable(),
  likely_anti_muslim_count: z.number().int().nonnegative().nullable(),
  coverage_score: z.number().min(0).max(1).nullable(),
});

export const WireDashboardTrendSchema = z.object({
  interval: z.enum(['hourly', 'daily', 'weekly']),
  points: z.array(WireTrendPointSchema),
});

export const WireDashboardInsightSchema = z.object({
  answer: z.string(),
  observations: z.array(z.string()),
  interpretation: z.array(z.string()),
  possible_association: z.array(z.string()),
  unknowns: z.array(z.string()),
  citations: z.array(z.string()),
});

export const WireHeadlineSchema = z.object({
  item_id: z.string(),
  headline: z.string(),
  source_name: z.string(),
  published_at: z.string(),
  country_code: z.string().nullable(),
  geographic_scope: z.string().nullable(),
  summary: z.string(),
  topic_labels: z.array(z.string()),
});

export const WireDashboardResponseSchema = z.object({
  coverage: WireCoverageSummarySchema,
  metrics: WireDashboardMetricsSchema,
  trend: WireDashboardTrendSchema,
  headlines: z.array(WireHeadlineSchema),
  insight: WireDashboardInsightSchema.nullable(),
  insight_unavailable_reason: z.string().nullable(),
  sampling_disclosure: z.string(),
  meta: WireMetaSchema,
});

export const WireRelevanceSchema = z.enum(['muslim_related', 'not_related', 'uncertain']);

export const WireStanceSchema = z.enum([
  'likely_anti_muslim',
  'non_hateful_discussion',
  'counterspeech_or_quotation',
  'uncertain',
]);

export const WireHateTypeSchema = z.enum([
  'animosity',
  'derogation',
  'dehumanization',
  'exclusion',
  'threat_or_incitement',
  'collective_blame',
  'other',
]);

export const WireReviewStateSchema = z.enum([
  'model_only',
  'pending_review',
  'confirmed',
  'corrected',
  'disputed',
  'needs_context',
]);

export const WireConfidenceTierSchema = z.enum(['low', 'medium', 'high']);

export const WireDatasetProvenanceSchema = z.object({
  provider: z.string(),
  name: z.string(),
  version: z.string(),
  license_id: z.string().nullable(),
  landing_page_url: z.string().nullable(),
});

export const WireItemSummarySchema = z.object({
  id: z.string(),
  content_kind: z.enum(['news_article', 'social_post', 'social_comment', 'dataset_record']),
  platform: z.enum([
    'youtube',
    'reddit',
    'bluesky',
    'news_web',
    'user_submitted',
    'not_applicable',
  ]),
  title: z.string().nullable(),
  permitted_excerpt: z.string().nullable(),
  publisher_or_container: z.string().nullable(),
  canonical_url: z.string().nullable(),
  published_at: z.string().nullable(),
  observed_at: z.string(),
  language: z.string().nullable(),
  country_code: z.string().nullable(),
  source_status: z.enum(['available', 'inaccessible', 'deleted']),
  is_fixture: z.boolean(),
  dataset: WireDatasetProvenanceSchema.nullable().optional(),
  relevance: WireRelevanceSchema.nullable(),
  stance: WireStanceSchema.nullable(),
  hate_types: z.array(WireHateTypeSchema),
  severity: z.number().int().min(0).max(3).nullable(),
  confidence_tier: WireConfidenceTierSchema.nullable(),
  review_state: WireReviewStateSchema,
  requires_review: z.boolean(),
  is_classified: z.boolean(),
  platform_display: z.string(),
});

/**
 * `GET /v1/items/{id}`. Extends the summary with the model disclosure a
 * classification must never be shown without: the score, the model, prompt, and
 * taxonomy versions behind it, when it ran, its rationale, and the stated
 * limitations of the sample it came from.
 */
export const WireItemDetailSchema = WireItemSummarySchema.extend({
  score: z.number().min(0).max(1).nullable(),
  model_name: z.string().nullable(),
  model_version: z.string().nullable(),
  prompt_version: z.string().nullable(),
  taxonomy_version: z.string().nullable(),
  inferred_at: z.string().nullable(),
  rationale: z.string().nullable(),
  narrative_tags: z.array(z.string()),
  limitations: z.array(z.string()),
  sampling_disclosure: z.string(),
});

export const WireItemDetailResponseSchema = z.object({
  item: WireItemDetailSchema,
  meta: WireMetaSchema,
});

export const WirePageInfoSchema = z.object({
  next_cursor: z.string().nullable(),
  limit: z.number().int().positive(),
});

export const WireItemsPageSchema = z.object({
  items: z.array(WireItemSummarySchema),
  page: WirePageInfoSchema,
  meta: WireMetaSchema,
});

export const WireDatasetOptionSchema = z.object({
  provider: z.string(),
  name: z.string(),
  version: z.string(),
});

export const WireFilterOptionsSchema = z.object({
  content_kinds: z.array(z.string()),
  platforms: z.array(z.string()),
  datasets: z.array(WireDatasetOptionSchema),
  country_codes: z.array(z.string()),
  narrative_tags: z.array(z.string()),
  severities: z.array(z.number().int()),
  review_states: z.array(z.string()),
  confidence_tiers: z.array(z.string()),
  sorts: z.array(z.string()),
  max_window_days: z.number().int().positive(),
  max_page_limit: z.number().int().positive(),
  meta: WireMetaSchema,
});

export const WireInsightSummarySchema = z.object({
  id: z.string(),
  author_id: z.string(),
  author_display_name: z.string().nullable(),
  title: z.string(),
  claim: z.string(),
  metric: z.string(),
  numerator: z.number().int().nonnegative(),
  denominator: z.number().int().nonnegative(),
  window_start: z.string(),
  window_end: z.string(),
  figure_label: z.string(),
  filter_hash: z.string(),
  explorer_href: z.string(),
  source_keys: z.array(z.string()),
  items_observed: z.number().int().nonnegative(),
  items_relevant: z.number().int().nonnegative(),
  created_at: z.string(),
  value: z.number().nullable(),
});

export const WireInsightsPageSchema = z.object({
  items: z.array(WireInsightSummarySchema),
  page: WirePageInfoSchema,
  meta: WireMetaSchema,
});

export const WireInsightResponseSchema = z.object({
  insight: WireInsightSummarySchema,
  meta: WireMetaSchema,
});

export const WireCaptureSchema = z.object({
  id: z.string(),
  alt_text: z.string(),
  image_source: z.string(),
  filter_hash: z.string(),
  explorer_href: z.string(),
  created_at: z.string(),
});

export const WireCaptureResponseSchema = z.object({
  capture: WireCaptureSchema,
  meta: WireMetaSchema,
});

export const WireReactionCountsSchema = z.object({
  useful: z.number().int().nonnegative(),
  needs_context: z.number().int().nonnegative(),
  viewer: z.enum(['useful', 'needs_context']).nullable(),
});

export const WireDiscussionPostSchema = z.object({
  id: z.string(),
  snapshot_insight_id: z.string(),
  author_id: z.string(),
  author_display_name: z.string().nullable(),
  body: z.string(),
  created_at: z.string(),
  retracted_at: z.string().nullable(),
  capture: WireCaptureSchema.nullable(),
  reactions: WireReactionCountsSchema,
});

export const WireDiscussionResponseSchema = z.object({
  insight_id: z.string(),
  posts: z.array(WireDiscussionPostSchema),
  can_participate: z.boolean(),
  meta: WireMetaSchema,
});

export const WirePostResponseSchema = z.object({
  post: WireDiscussionPostSchema,
  meta: WireMetaSchema,
});

export const WireViewerPostSchema = WireDiscussionPostSchema.extend({
  insight_title: z.string(),
});

export const WireViewerPostsPageSchema = z.object({
  items: z.array(WireViewerPostSchema),
  page: WirePageInfoSchema,
  meta: WireMetaSchema,
});

export const WireProfileSchema = z.object({
  user_id: z.string(),
  role: z.enum(['registered_user', 'reviewer', 'administrator']),
  display_name: z.string().nullable(),
  onboarding_status: z.enum(['not_started', 'in_progress', 'completed']),
  content_safety_preferences: z.record(z.string(), z.unknown()),
});

export const WireCurrentUserResponseSchema = z.object({
  profile: WireProfileSchema,
  meta: WireMetaSchema,
});

export const WireAssistantReplySchema = z.object({
  answer: z.string(),
  citations: z.array(
    z.object({
      kind: z.enum(['metric', 'coverage', 'methodology']),
      id: z.string(),
      label: z.string(),
    }),
  ),
  limitations: z.array(z.string()),
  grounded_in: z.enum(['figures', 'methodology', 'none']),
  meta: WireMetaSchema,
});

export const WirePolicyCandidateSchema = z.object({
  platform_policy_id: z.string(),
  platform: z.string(),
  policy_key: z.string(),
  title: z.string(),
  summary: z.string(),
  official_url: z.string(),
  version: z.string(),
  last_reviewed_at: z.string().nullable(),
  recipient_kind: z.enum(['official_form', 'allowlist_email']),
  official_report_url: z.string().nullable(),
  score: z.number().min(0).max(1),
  confidence_tier: WireConfidenceTierSchema,
  rationale: z.string(),
});

export const WirePolicyAnalysisSchema = z.object({
  content_item_id: z.string(),
  candidates: z.array(WirePolicyCandidateSchema),
  matcher_version: z.string(),
  disclosure: z.string(),
  meta: WireMetaSchema,
});

export const WirePreparedReportSchema = z.object({
  id: z.string(),
  content_item_id: z.string(),
  platform: z.string(),
  platform_policy_id: z.string(),
  policy_version: z.string(),
  evidence_summary: z.string(),
  suggested_text: z.string(),
  status: z.enum(['prepared', 'submitted', 'closed']),
  recipient_kind: z.enum(['official_form', 'allowlist_email']),
  recipient_address: z.string().nullable(),
  draft_subject: z.string().nullable(),
  submitted_at: z.string().nullable(),
  outcome: z
    .enum(['no_response', 'content_removed', 'content_restricted', 'no_violation', 'other'])
    .nullable(),
  outcome_note: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const WirePreparedReportResponseSchema = z.object({
  report: WirePreparedReportSchema,
  meta: WireMetaSchema,
});

export const WireContributionSummarySchema = z.object({
  id: z.string(),
  contribution_type: z.enum([
    'url_submission',
    'classification_dispute',
    'prepared_platform_report',
  ]),
  label: z.string(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
  destination_item_id: z.string().nullable(),
});

export const WireContributionsPageSchema = z.object({
  items: z.array(WireContributionSummarySchema),
  page: WirePageInfoSchema,
  meta: WireMetaSchema,
});

export const WireReportMetricSnapshotSchema = z.object({
  key: z.string(),
  value: z.number().nullable(),
  numerator: z.number().int().nonnegative().nullable(),
  denominator: z.number().int().nonnegative().nullable(),
});

export const WireReportFindingSchema = z.object({
  key: z.string(),
  statement: z.string(),
  citation_ids: z.array(z.string()),
});

export const WireReportCitationSchema = z.object({
  id: z.string(),
  kind: z.string(),
  label: z.string(),
});

export const WireResearchReportSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  title: z.string(),
  filter_hash: z.string(),
  filters: z.record(z.string(), z.unknown()),
  data_version: z.string(),
  coverage: WireCoverageSummarySchema,
  metrics: z.array(WireReportMetricSnapshotSchema),
  findings: z.array(WireReportFindingSchema),
  citations: z.array(WireReportCitationSchema),
  methodology_version: z.string(),
  methodology_disclosure: z.record(z.string(), z.unknown()),
  limitations: z.array(z.string()),
  source_scope: z.array(z.string()),
  window_start: z.string(),
  window_end: z.string(),
  data_mode: WireDataModeSchema,
  redaction_mode: z.enum(['default_redacted', 'aggregate_only']),
  status: z.enum(['pending', 'ready', 'failed']),
  aggregate_csv_available: z.boolean(),
  created_at: z.string(),
  completed_at: z.string(),
});

export const WireResearchReportResponseSchema = z.object({
  report: WireResearchReportSchema,
  meta: WireMetaSchema,
});

export const WireDatasetAnnotationSchema = z.object({
  hate_types: z.array(WireHateTypeSchema),
  severity: z.number().int().min(0).max(3).nullable(),
  note: z.string(),
});

export const WireImageExampleSchema = z.object({
  id: z.string(),
  title: z.string(),
  image_url: z.string(),
  image_url_expires_at: z.string(),
  alt_text: z.string().min(1),
  form_note: z.string(),
  dataset_annotation: WireDatasetAnnotationSchema,
  relevance: WireRelevanceSchema.nullable(),
  stance: WireStanceSchema.nullable(),
  score: z.number().min(0).max(1).nullable(),
  confidence_tier: WireConfidenceTierSchema.nullable(),
  narrative_tags: z.array(z.string()),
  rationale: z.string().nullable(),
});

export const WireImageManifestSchema = z.object({
  dataset_provider: z.string(),
  dataset_name: z.string(),
  dataset_version: z.string(),
  license_identifier: z.string(),
  schema_mapping_version: z.string(),
  approval_state: z.string(),
  reviewer: z.string(),
});

export const WireImageExampleListSchema = z.object({
  data_mode: WireDataModeSchema,
  manifest: WireImageManifestSchema.nullable(),
  items: z.array(WireImageExampleSchema),
  disclosure: z.string(),
  meta: WireMetaSchema,
});

/**
 * `POST /v1/image-uploads` (B-S28). Carries no storage path and no filename:
 * the identifier is how the image is referred to afterwards, and the link is
 * short-lived and minted per request.
 */
export const WireImageUploadSchema = z.object({
  upload_id: z.string(),
  mime_type: z.string(),
  byte_size: z.number().int().positive(),
  pixel_width: z.number().int().positive(),
  pixel_height: z.number().int().positive(),
  sha256: z.string(),
  is_new: z.boolean(),
  retention_expires_at: z.string().nullable(),
  image_url: z.string(),
  image_url_expires_at: z.string(),
  disclosure: z.string(),
  meta: WireMetaSchema,
});

export const WireImageClassificationSchema = z.object({
  example_id: z.string().nullable(),
  upload_id: z.string().nullable(),
  data_mode: WireDataModeSchema,
  relevance: WireRelevanceSchema,
  stance: WireStanceSchema,
  hate_types: z.array(WireHateTypeSchema),
  severity: z.number().int().min(0).max(3).nullable(),
  narrative_tags: z.array(z.string()),
  score: z.number().min(0).max(1),
  confidence_tier: WireConfidenceTierSchema,
  rationale: z.string(),
  model_name: z.string(),
  model_version: z.string(),
  taxonomy_version: z.string(),
  review_required: z.boolean(),
  dataset_annotation: WireDatasetAnnotationSchema.nullable(),
  status: z.string(),
  disclosure: z.string(),
  meta: WireMetaSchema,
});

export const WireErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().optional(),
    retryable: z.boolean().optional(),
  }),
});

export type WireDashboardResponse = z.infer<typeof WireDashboardResponseSchema>;
export type WireItemSummary = z.infer<typeof WireItemSummarySchema>;
export type WireItemDetail = z.infer<typeof WireItemDetailSchema>;
export type WireItemsPage = z.infer<typeof WireItemsPageSchema>;
export type WireFilterOptions = z.infer<typeof WireFilterOptionsSchema>;
export type WireInsightSummary = z.infer<typeof WireInsightSummarySchema>;
export type WireDiscussionPost = z.infer<typeof WireDiscussionPostSchema>;
export type WireDiscussionResponse = z.infer<typeof WireDiscussionResponseSchema>;
export type WireViewerPost = z.infer<typeof WireViewerPostSchema>;
export type WireProfile = z.infer<typeof WireProfileSchema>;
export type WireAssistantReply = z.infer<typeof WireAssistantReplySchema>;
export type WirePolicyCandidate = z.infer<typeof WirePolicyCandidateSchema>;
export type WirePolicyAnalysis = z.infer<typeof WirePolicyAnalysisSchema>;
export type WirePreparedReport = z.infer<typeof WirePreparedReportSchema>;
export type WireContributionSummary = z.infer<typeof WireContributionSummarySchema>;
export type WireContributionsPage = z.infer<typeof WireContributionsPageSchema>;
export type WireResearchReport = z.infer<typeof WireResearchReportSchema>;
export type WireImageExampleList = z.infer<typeof WireImageExampleListSchema>;
export type WireImageUpload = z.infer<typeof WireImageUploadSchema>;
export type WireImageClassification = z.infer<typeof WireImageClassificationSchema>;
export type WireCapture = z.infer<typeof WireCaptureSchema>;
