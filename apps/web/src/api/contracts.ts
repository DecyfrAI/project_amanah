import { z } from 'zod';

export const DateWindowSchema = z.object({
  from: z.string(),
  to: z.string(),
  timezone: z.string(),
});

export const CoverageSchema = z.object({
  sources: z.array(z.string()),
  itemsObserved: z.number().int().nonnegative(),
  itemsRelevant: z.number().int().nonnegative(),
  lastSuccessfulRun: z.string().nullable(),
  warnings: z.array(z.string()),
});

/**
 * The Overview's coverage, which is the strip everything else is scoped by.
 *
 * Extends the shared coverage with the container count, since "312 relevant of
 * 1483 observed" means something different across 22 videos than across 2.
 */
export const OverviewCoverageSchema = CoverageSchema.extend({
  /** Null when the provider does not report container counts (live dashboard). */
  containersMonitored: z.number().int().nonnegative().nullable(),
  containerLabel: z.string(),
});

/**
 * A KPI, carrying its own provenance.
 *
 * The numerator and denominator travel with the value rather than being
 * reconstructed in a component, because a rate without its denominator is the
 * single most misleading thing this product could display. A count has no
 * denominator, so both are nullable, and `insufficientVolume` lets the provider
 * refuse to state a rate that rests on too few items rather than emitting a
 * volatile one.
 */
export const OverviewMetricSchema = z.object({
  id: z.string(),
  label: z.string(),
  definition: z.string(),
  unit: z.enum(['count', 'rate']),
  value: z.number().nullable(),
  numerator: z.number().int().nonnegative().nullable(),
  denominator: z.number().int().nonnegative().nullable(),
  /** True while the figure rests on model output that no person has confirmed. */
  isModelOnly: z.boolean(),
  insufficientVolume: z.boolean(),
  changeVsBaseline: z
    .object({
      absolute: z.number(),
      percent: z.number(),
      baselineLabel: z.string(),
    })
    .nullable(),
});

/**
 * One day of collection.
 *
 * `collected: false` is not the same as zero, and the two must stay
 * distinguishable all the way to the chart: a failed collection day draws as a
 * break in the line, never as a drop to the axis. Counts are null on an
 * uncollected day so no arithmetic can quietly treat the gap as a real zero.
 */
export const OverviewDaySourceSchema = z.object({
  key: z.string(),
  label: z.string(),
  /** Likely-hate items from this source on this day. */
  likelyHate: z.number().int().nonnegative(),
  /** Muslim-related items from this source on this day. */
  relevant: z.number().int().nonnegative(),
});

export const OverviewDaySchema = z.object({
  date: z.string(),
  collected: z.boolean(),
  observed: z.number().int().nonnegative().nullable(),
  relevant: z.number().int().nonnegative().nullable(),
  likelyHate: z.number().int().nonnegative().nullable(),
  nonRelevant: z.number().int().nonnegative().nullable(),
  /**
   * Likely-hate and relevant counts by source, largest first.
   * Empty when the day was not collected, so a gap stays a gap.
   */
  sources: z.array(OverviewDaySourceSchema),
});

/**
 * One row of a breakdown, carrying the pair the rate came from.
 *
 * The denominator is explicit and named at the breakdown level rather than
 * implied, because it is not the same population on every axis: a type share
 * divides by Muslim-related items, a review-state share divides by the
 * classifications themselves. `rate` is null where the denominator is too small
 * to state one, rather than a number the reader has no way to distrust.
 */
export const BreakdownRowSchema = z.object({
  key: z.string(),
  label: z.string(),
  count: z.number().int().nonnegative(),
  denominator: z.number().int().nonnegative(),
  rate: z.number().nullable(),
});

/**
 * A composition of the likely-hate items along one axis.
 *
 * `dimension` names the axis so a component can offer the matching drill-down
 * filter without guessing from the label, and `definition` carries the sentence
 * that keeps the reader from over-reading the shares.
 */
export const OverviewBreakdownSchema = z.object({
  id: z.string(),
  label: z.string(),
  dimension: z.enum(['hate_type', 'platform', 'severity', 'review_state']),
  definition: z.string(),
  total: z.number().int().nonnegative(),
  /** What one unit of `count` is, for example "items classified as likely hate". */
  countLabel: z.string(),
  /** What `denominator` counts, for example "Muslim-related items". */
  denominatorLabel: z.string(),
  rows: z.array(BreakdownRowSchema),
});

/**
 * The filters the response was actually computed under.
 *
 * Echoed back rather than assumed from the URL, so the screen can state its own
 * scope truthfully even if a filter was rejected or clamped at the boundary.
 */
export const AppliedFiltersSchema = z.object({
  from: z.string(),
  to: z.string(),
  platforms: z.array(z.string()),
  hateTypes: z.array(z.string()),
  severityBands: z.array(z.string()),
  reviewStates: z.array(z.string()),
});

export const OverviewSchema = z.object({
  window: DateWindowSchema,
  coverage: OverviewCoverageSchema,
  applied: AppliedFiltersSchema,
  metrics: z.array(OverviewMetricSchema),
  daily: z.array(OverviewDaySchema),
  breakdowns: z.array(OverviewBreakdownSchema),
});

export const FilterOptionSchema = z.object({
  value: z.string(),
  label: z.string(),
  /** Items matching this option in the full available range, or null if unknown. */
  count: z.number().int().nonnegative().nullable(),
});

/**
 * What the interface is allowed to ask for.
 *
 * `available` is the range that has data at all, which is what the calendar must
 * bound itself to: offering a date with no collection behind it invites a reader
 * to mistake an empty response for a quiet day.
 */
export const FilterOptionsSchema = z.object({
  /** Null when the provider does not report an available-data window (live). */
  available: DateWindowSchema.nullable(),
  defaultWindowDays: z.number().int().positive(),
  platforms: z.array(FilterOptionSchema),
  /** Empty when the provider does not support this filter axis. */
  hateTypes: z.array(FilterOptionSchema),
  severityBands: z.array(FilterOptionSchema),
  reviewStates: z.array(FilterOptionSchema),
});

/**
 * One collected item, as the Explorer is allowed to show it.
 *
 * The focal content is a synthetic excerpt shown in full: othering remarks, never
 * a real slur or a real handle. Context that is genuinely public, the container
 * title and the platform, travels intact, because a figure without context cannot
 * be checked. There is no author field on purpose: person-level views are out of
 * scope. The wire field remains `redactedExcerpt` so live responses keep the
 * agreed name.
 */
/**
 * Optional image payload on an Explorer row.
 *
 * Filename, size, mime, and a public path. Pixels never travel as bytes on
 * this contract. The form note describes layout, not slogans.
 */
export const ExplorerItemImageSchema = z.object({
  exampleId: z.string(),
  filename: z.string(),
  byteSize: z.number().int().nonnegative(),
  mime: z.string(),
  imageSrc: z.string(),
  altText: z.string().min(1),
  formNote: z.string(),
});

/**
 * Dataset lineage for an item imported from a reviewed open datapack.
 * Such items publish `N/A` as their platform; this block is how a reader
 * still learns where the row came from.
 */
export const ExplorerItemDatasetSchema = z.object({
  provider: z.string(),
  name: z.string(),
  version: z.string(),
  licenseId: z.string().nullable(),
  landingPageUrl: z.string().nullable(),
});

export const ExplorerItemSchema = z.object({
  id: z.string(),
  date: z.string(),
  platform: z.string(),
  /** Human-facing platform label; open-datapack rows display as `N/A`. */
  platformDisplay: z.string().optional(),
  containerTitle: z.string().nullable(),
  containerUrl: z.string().nullable(),
  /** Licensed or fair-use excerpt only. Null when none is permitted. */
  redactedExcerpt: z.string().nullable(),
  /**
   * Null until the item has a successful prediction. "Collected, not yet
   * analysed" is a real state and must never default to a judgement.
   */
  relevance: z.enum(['muslim_related', 'not_related', 'uncertain']).nullable(),
  classification: z.enum(['likely_hate', 'not_hate']).nullable(),
  hateType: z.string().nullable(),
  severity: z.number().int().min(0).max(3).nullable(),
  /** Model score, never described to a reader as certainty. Null when unclassified. */
  modelScore: z.number().min(0).max(1).nullable(),
  /**
   * Provider vocabulary: the live service uses `model_only`, `pending_review`,
   * `confirmed`, `corrected`, `disputed`, `needs_context`; older fixtures use
   * `pending`, `confirmed`, `corrected`. Labels come from `reviewLabel`.
   */
  reviewState: z.string(),
  reviewNote: z.string().nullable(),
  isFixture: z.boolean().optional(),
  dataset: ExplorerItemDatasetSchema.nullable().optional(),
  image: ExplorerItemImageSchema.nullable().optional(),
});

/**
 * One item on its own page (F-S8).
 *
 * Extends the row with the disclosure a classification must never appear
 * without: the score, the versions that produced it, when it ran, the model's
 * rationale, and what this sample cannot support. Every one of these is
 * nullable, because an item that has not been classified is a real state and
 * must not be dressed as a finding.
 */
export const ExplorerItemDetailSchema = ExplorerItemSchema.extend({
  modelName: z.string().nullable(),
  modelVersion: z.string().nullable(),
  promptVersion: z.string().nullable(),
  taxonomyVersion: z.string().nullable(),
  inferredAt: z.string().nullable(),
  rationale: z.string().nullable(),
  narrativeTags: z.array(z.string()),
  limitations: z.array(z.string()),
  samplingDisclosure: z.string(),
});

export const ExplorerPageSchema = z.object({
  applied: AppliedFiltersSchema,
  /** Total matches, or null when keyset pagination cannot count them. */
  matched: z.number().int().nonnegative().nullable(),
  returned: z.number().int().nonnegative(),
  /** Opaque cursor for the next page, or null on the last page. */
  nextCursor: z.string().nullable(),
  items: z.array(ExplorerItemSchema),
});

export const InsightFactSchema = z.object({
  id: z.string(),
  claim: z.string(),
  numerator: z.number().int().nonnegative(),
  denominator: z.number().int().nonnegative(),
  metric: z.string(),
});

export const InsightCitationSchema = z.object({
  kind: z.enum(['figure', 'item', 'coverage']),
  id: z.string(),
  label: z.string(),
});

export const InsightGenerationSchema = z.object({
  model: z.string(),
  generatedAt: z.string(),
  isMachineGenerated: z.boolean(),
});

export const InsightSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string(),
  window: DateWindowSchema,
  coverage: CoverageSchema,
  facts: z.array(InsightFactSchema),
  citations: z.array(InsightCitationSchema),
  generation: InsightGenerationSchema,
});

export const InsightListSchema = z.object({
  insights: z.array(InsightSchema),
});

export const ReactionKindSchema = z.enum(['useful', 'needs_context']);

export const DiscussantSchema = z.object({
  id: z.string(),
  displayName: z.string(),
});

export const DashboardCaptureSchema = z.object({
  id: z.string(),
  altText: z.string().min(1),
  imageSrc: z.string(),
  filterHash: z.string(),
  explorerHref: z.string(),
});

export const PostReactionsSchema = z.object({
  useful: z.number().int().nonnegative(),
  needs_context: z.number().int().nonnegative(),
  viewer: ReactionKindSchema.nullable(),
});

export const DiscussionPostSchema = z.object({
  id: z.string(),
  author: DiscussantSchema,
  body: z.string(),
  createdAt: z.string(),
  retractedAt: z.string().nullable(),
  capture: DashboardCaptureSchema.nullable(),
  reactions: PostReactionsSchema,
});

export const DiscussionSchema = z.object({
  insightId: z.string(),
  threadId: z.string(),
  posts: z.array(DiscussionPostSchema),
  /** Whether the caller holds an invitation to post (ADR 0004). Absent means yes. */
  canParticipate: z.boolean().optional(),
});

export const DiscussionCatalogSchema = z.object({
  threads: z.array(DiscussionSchema),
});

export const CreatePostInputSchema = z.object({
  body: z.string().min(1),
  captureId: z.string().optional(),
});

export const CreateCaptureInputSchema = z.object({
  altText: z.string().min(1),
  imageSrc: z.string(),
  filterHash: z.string(),
  explorerHref: z.string(),
});

/**
 * A snapshot started from a figure or a day.
 *
 * The counts travel with the claim so a later reader can check the insight
 * against the same numbers the author was looking at. `explorerHref` is the
 * filter state at the moment of capture, not a live query.
 */
export const CreateInsightInputSchema = z.object({
  title: z.string().min(1),
  claim: z.string().min(1),
  numerator: z.number().int().nonnegative(),
  denominator: z.number().int().nonnegative(),
  metric: z.string(),
  from: z.string(),
  to: z.string(),
  explorerHref: z.string(),
  figureLabel: z.string(),
  sources: z.array(z.string()),
  itemsObserved: z.number().int().nonnegative(),
  itemsRelevant: z.number().int().nonnegative(),
});

/**
 * One of the viewer's own notes, with enough of the parent insight to find it.
 *
 * Profile shows these so a person can return to a discussion they joined without
 * walking every insight. The body is still the note, not a new kind of post.
 */
export const ViewerPostSchema = DiscussionPostSchema.extend({
  insightId: z.string(),
  insightTitle: z.string(),
});

export const ViewerPostListSchema = z.object({
  posts: z.array(ViewerPostSchema),
});

/**
 * A question about the current window, carrying the same filters the figures use.
 *
 * The assistant must not invent a rate. It answers from stored figures, and a
 * later retrieval step may add methodology text. The filters travel with the
 * question so the reply cannot quietly describe a different sample.
 */
export const AssistantAskInputSchema = z.object({
  question: z.string().min(1),
  from: z.string().optional(),
  to: z.string().optional(),
  platforms: z.array(z.string()).optional(),
  hateTypes: z.array(z.string()).optional(),
  severityBands: z.array(z.string()).optional(),
  reviewStates: z.array(z.string()).optional(),
});

export const AssistantCitationSchema = z.object({
  kind: z.enum(['metric', 'coverage', 'methodology']),
  id: z.string(),
  label: z.string(),
});

export const AssistantReplySchema = z.object({
  answer: z.string(),
  citations: z.array(AssistantCitationSchema),
  limitations: z.array(z.string()),
  groundedIn: z.enum(['figures', 'methodology', 'none']),
});

/**
 * One published news article, used as coinciding context on Overview.
 *
 * This is not a classified item. There is no hate label, model score, or review
 * state: Amanah did not judge the article. Wire fields stay snake_case so the
 * live `/v1/news` response can be validated without a reshape.
 */
export const NewsItemSchema = z.object({
  id: z.string(),
  source_name: z.string(),
  source_homepage: z.string(),
  title: z.string(),
  /** Plain text only. HTML from a feed description must be stripped first. */
  summary: z.string(),
  url: z.string(),
  /** Null when the feed stated no publication time; never the retrieval time. */
  published_at: z.string().nullable(),
  retrieved_at: z.string(),
  language: z.string(),
  /** Null when the source stated no scope; never coerced to the nearer value. */
  scope: z.enum(['local', 'global']).nullable(),
  location: z.string().nullable(),
});

export const NewsCoverageSchema = z.object({
  sources: z.array(z.string()),
  items_retrieved: z.number().int().nonnegative(),
  last_successful_run: z.string().nullable(),
  warnings: z.array(z.string()),
});

export const NewsListSchema = z.object({
  window: DateWindowSchema,
  applied: z.object({
    from: z.string(),
    to: z.string(),
  }),
  coverage: NewsCoverageSchema,
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  next_cursor: z.string().nullable(),
  items: z.array(NewsItemSchema),
});

/**
 * Assisted platform-report draft (F-S14).
 *
 * The screenshot never crosses this boundary: only filename and byte size are
 * sent, so a live backend can record that evidence existed without receiving it.
 * Quoted wording is the reporter's own note, or a synthetic fixture line, and
 * is not redacted.
 */
export const ReportPlatformSchema = z.enum(['youtube', 'reddit', 'other']);

export const ReportDraftRequestSchema = z.object({
  platform: ReportPlatformSchema,
  reporter_note: z.string().max(2000).optional(),
  content_url: z
    .string()
    .max(2000)
    .regex(/^https?:\/\/.+/i)
    .optional(),
  has_image: z.boolean(),
  image_filename: z.string().max(255).optional(),
  image_byte_size: z.number().int().nonnegative().optional(),
  source_item_id: z.string().max(64).optional(),
});

export const ReportDraftSchema = z.object({
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  platform: ReportPlatformSchema,
  platform_label: z.string(),
  to: z.string(),
  to_kind: z.enum(['placeholder', 'allowlist']),
  to_note: z.string(),
  official_report_url: z.string().nullable(),
  official_report_label: z.string().nullable(),
  subject: z.string(),
  body: z.string(),
  likely_quote: z.string(),
  platform_guess: ReportPlatformSchema,
  confidence: z.number().min(0).max(1),
  model_name: z.string(),
  model_version: z.string(),
  status: z.literal('prepared_not_sent'),
  disclosure: z.string(),
});

export type DateWindow = z.infer<typeof DateWindowSchema>;
export type Coverage = z.infer<typeof CoverageSchema>;
export type OverviewCoverage = z.infer<typeof OverviewCoverageSchema>;
export type OverviewMetric = z.infer<typeof OverviewMetricSchema>;
export type OverviewDay = z.infer<typeof OverviewDaySchema>;
export type OverviewDaySource = z.infer<typeof OverviewDaySourceSchema>;
export type BreakdownRow = z.infer<typeof BreakdownRowSchema>;
export type OverviewBreakdown = z.infer<typeof OverviewBreakdownSchema>;
export type AppliedFilters = z.infer<typeof AppliedFiltersSchema>;
export type Overview = z.infer<typeof OverviewSchema>;
export type FilterOption = z.infer<typeof FilterOptionSchema>;
export type FilterOptions = z.infer<typeof FilterOptionsSchema>;
export type ExplorerItemImage = z.infer<typeof ExplorerItemImageSchema>;
export type ExplorerItemDataset = z.infer<typeof ExplorerItemDatasetSchema>;
export type ExplorerItem = z.infer<typeof ExplorerItemSchema>;
export type ExplorerItemDetail = z.infer<typeof ExplorerItemDetailSchema>;
export type ExplorerPage = z.infer<typeof ExplorerPageSchema>;
export type Insight = z.infer<typeof InsightSchema>;
export type InsightList = z.infer<typeof InsightListSchema>;
export type ReactionKind = z.infer<typeof ReactionKindSchema>;
export type Discussant = z.infer<typeof DiscussantSchema>;
export type DashboardCapture = z.infer<typeof DashboardCaptureSchema>;
export type PostReactions = z.infer<typeof PostReactionsSchema>;
export type DiscussionPost = z.infer<typeof DiscussionPostSchema>;
export type Discussion = z.infer<typeof DiscussionSchema>;
export type DiscussionCatalog = z.infer<typeof DiscussionCatalogSchema>;
export type CreatePostInput = z.infer<typeof CreatePostInputSchema>;
export type CreateCaptureInput = z.infer<typeof CreateCaptureInputSchema>;
export type CreateInsightInput = z.infer<typeof CreateInsightInputSchema>;
export type ViewerPost = z.infer<typeof ViewerPostSchema>;
export type ViewerPostList = z.infer<typeof ViewerPostListSchema>;
export type AssistantAskInput = z.infer<typeof AssistantAskInputSchema>;
export type AssistantCitation = z.infer<typeof AssistantCitationSchema>;
export type AssistantReply = z.infer<typeof AssistantReplySchema>;
export type NewsItem = z.infer<typeof NewsItemSchema>;
export type NewsCoverage = z.infer<typeof NewsCoverageSchema>;
export type NewsList = z.infer<typeof NewsListSchema>;
export type ReportPlatform = z.infer<typeof ReportPlatformSchema>;
export type ReportDraftRequest = z.infer<typeof ReportDraftRequestSchema>;
export type ReportDraft = z.infer<typeof ReportDraftSchema>;

/**
 * Staged image classification (spec §9.5). Filename and size only: pixels
 * never cross this boundary. Original datapack labels stay separate from the
 * Amanah prediction.
 */
export const HateTypeSchema = z.enum([
  'animosity',
  'derogation',
  'dehumanization',
  'exclusion',
  'threat_or_incitement',
  'collective_blame',
  'other',
]);

export const StanceSchema = z.enum([
  'likely_anti_muslim',
  'non_hateful_discussion',
  'counterspeech_or_quotation',
  'uncertain',
]);

export const RelevanceSchema = z.enum(['muslim_related', 'not_related', 'uncertain']);

export const ConfidenceTierSchema = z.enum(['low', 'medium', 'high']);

export const EvidenceClassifyRequestSchema = z.object({
  image_filename: z.string().min(1).max(255),
  image_byte_size: z.number().int().nonnegative(),
  example_id: z.string().max(64).optional(),
  /** An image the person uploaded through `POST /v1/image-uploads` (B-S28). */
  upload_id: z.string().max(64).optional(),
});

/**
 * One stored upload (B-S28).
 *
 * `imageSrc` is a short-lived signed URL, never a durable location, and there is
 * no field for the storage path or the original filename. `isNew` is false when
 * the same picture was already stored, so the interface does not claim to have
 * saved it twice.
 */
export const ImageUploadSchema = z.object({
  uploadId: z.string(),
  mimeType: z.string(),
  byteSize: z.number().int().positive(),
  pixelWidth: z.number().int().positive(),
  pixelHeight: z.number().int().positive(),
  isNew: z.boolean(),
  imageSrc: z.string(),
  retentionExpiresAt: z.string().nullable(),
  disclosure: z.string(),
});

export const DatasetAnnotationSchema = z.object({
  hate_types: z.array(HateTypeSchema),
  severity: z.number().int().min(0).max(3).nullable(),
  note: z.string(),
});

export const ImageClassificationSchema = z.object({
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  example_id: z.string(),
  relevance: RelevanceSchema,
  stance: StanceSchema,
  classification: z.enum(['likely_hate', 'not_hate']),
  hate_types: z.array(HateTypeSchema),
  severity: z.number().int().min(0).max(3).nullable(),
  narrative_tags: z.array(z.string()),
  score: z.number().min(0).max(1),
  confidence_tier: ConfidenceTierSchema,
  rationale: z.string(),
  model_name: z.string(),
  model_version: z.string(),
  taxonomy_version: z.string(),
  review_required: z.boolean(),
  dataset_annotation: DatasetAnnotationSchema.nullable(),
  status: z.literal('classified_not_reviewed'),
  disclosure: z.string(),
});

export const ImageExampleSchema = z.object({
  id: z.string(),
  title: z.string(),
  /** Fixture asset path, or a short-lived signed URL on live. Never store it. */
  image_src: z.string(),
  alt_text: z.string().min(1),
  form_note: z.string(),
  dataset_annotation: DatasetAnnotationSchema,
  /** Null when the image has not been classified. Never means "safe". */
  score: z.number().min(0).max(1).nullable(),
  narrative_tags: z.array(z.string()),
  rationale: z.string().nullable(),
});

export const ImageExampleListSchema = z.object({
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  manifest: z
    .object({
      dataset_provider: z.string(),
      dataset_name: z.string(),
      dataset_version: z.string(),
      license_identifier: z.string(),
      schema_mapping_version: z.string(),
      approval_state: z.string(),
      reviewer: z.string(),
    })
    .nullable(),
  items: z.array(ImageExampleSchema),
});

/**
 * Immutable research-report snapshot (spec §16).
 *
 * Aggregate only: counts and their denominators, never an item. A snapshot
 * freezes the figures at the moment it was generated, so a report cited later
 * still states what was true when it was made rather than re-querying and
 * quietly changing. Wire fields stay snake_case to match the FastAPI payload.
 */
export const ReportMetricKeySchema = z.enum([
  'observed_count',
  'muslim_related_count',
  'likely_anti_muslim_count',
  'reviewed_count',
  'likely_anti_muslim_rate',
]);

export const ReportFindingKeySchema = z.enum(['monitored_sample_rate', 'analysis_coverage']);

export const RedactionModeSchema = z.enum(['default_redacted', 'aggregate_only']);

/**
 * The filter subset a report may freeze.
 *
 * Deliberately narrower than the dashboard's filters: the backend `ItemFilters`
 * has no hate-type axis, so a report cannot claim a scope the service cannot
 * reproduce. A hate-type selection on screen is not carried into the snapshot.
 */
export const ResearchReportFiltersSchema = z.object({
  date_from: z.string().optional(),
  date_to: z.string().optional(),
  platforms: z.array(z.string()).max(25).optional(),
  severities: z.array(z.string()).max(25).optional(),
  review_states: z.array(z.string()).max(25).optional(),
});

export const CreateResearchReportRequestSchema = z.object({
  title: z.string().min(3).max(200),
  filters: ResearchReportFiltersSchema,
  metrics: z.array(ReportMetricKeySchema).min(1).max(5),
  findings: z.array(ReportFindingKeySchema).max(2),
  include_aggregate_csv: z.boolean(),
  redaction_mode: RedactionModeSchema,
});

export const ReportMetricSnapshotSchema = z.object({
  key: ReportMetricKeySchema,
  value: z.number().nullable(),
  numerator: z.number().int().nonnegative().nullable(),
  denominator: z.number().int().nonnegative().nullable(),
});

export const ReportFindingSnapshotSchema = z.object({
  key: ReportFindingKeySchema,
  statement: z.string().min(1).max(1000),
  citation_ids: z.array(z.string()).min(1),
});

export const ReportCitationSchema = z.object({
  id: z.string().min(1).max(200),
  kind: z.enum(['aggregate', 'methodology']),
  label: z.string().min(1).max(500),
});

export const ReportCoverageSchema = z.object({
  last_success_at: z.string().nullable(),
  coverage_score: z.number().min(0).max(1).nullable(),
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  is_stale: z.boolean(),
  warnings: z.array(z.string()),
});

export const ResearchReportSchema = z.object({
  id: z.string(),
  title: z.string(),
  /** SHA-256 of the exact filters. Two reports of the same scope share it. */
  filter_hash: z.string().regex(/^[0-9a-f]{64}$/),
  filters: ResearchReportFiltersSchema,
  data_version: z.string(),
  coverage: ReportCoverageSchema,
  metrics: z.array(ReportMetricSnapshotSchema),
  findings: z.array(ReportFindingSnapshotSchema),
  citations: z.array(ReportCitationSchema),
  methodology_version: z.string(),
  limitations: z.array(z.string()),
  source_scope: z.array(z.string()),
  window_start: z.string(),
  window_end: z.string(),
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  redaction_mode: RedactionModeSchema,
  status: z.enum(['pending', 'ready', 'failed']),
  aggregate_csv_available: z.boolean(),
  created_at: z.string(),
  completed_at: z.string(),
});

export type ReportMetricKey = z.infer<typeof ReportMetricKeySchema>;
export type ReportFindingKey = z.infer<typeof ReportFindingKeySchema>;
export type RedactionMode = z.infer<typeof RedactionModeSchema>;
export type ResearchReportFilters = z.infer<typeof ResearchReportFiltersSchema>;
export type CreateResearchReportRequest = z.infer<typeof CreateResearchReportRequestSchema>;
export type ReportMetricSnapshot = z.infer<typeof ReportMetricSnapshotSchema>;
export type ReportFindingSnapshot = z.infer<typeof ReportFindingSnapshotSchema>;
export type ReportCitation = z.infer<typeof ReportCitationSchema>;
export type ResearchReport = z.infer<typeof ResearchReportSchema>;

/**
 * Reviewer queue and its append-only decisions (spec §17).
 *
 * A queue entry carries the item and the prediction a reviewer has to judge, and
 * deliberately not the identity of whoever disputed it. A decision is appended:
 * the response is the event that was written, never a rewritten prediction, so a
 * later reader can still see what the model proposed and who disagreed.
 */
export const ReviewTaskTypeSchema = z.enum([
  'dispute',
  'low_confidence',
  'severity_escalation',
  'model_disagreement',
  'uncertain_relevance',
  'invalid_output',
]);

export const ReviewTaskStatusSchema = z.enum(['open', 'claimed', 'completed', 'cancelled']);

export const ReviewDecisionSchema = z.enum(['confirmed', 'corrected', 'needs_context', 'rejected']);

export const ReviewTaskSchema = z.object({
  id: z.string(),
  content_item_id: z.string(),
  prediction_id: z.string(),
  task_type: ReviewTaskTypeSchema,
  reason: z.string(),
  priority: z.number().int().nonnegative(),
  status: ReviewTaskStatusSchema,
  assigned_to: z.string().nullable(),
  claim_expires_at: z.string().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),

  title: z.string().nullable(),
  permitted_excerpt: z.string().nullable(),
  canonical_url: z.string().nullable(),
  platform: z.string(),

  relevance: RelevanceSchema,
  stance: StanceSchema,
  hate_types: z.array(HateTypeSchema),
  severity: z.number().int().min(0).max(3),
  score: z.number().min(0).max(1),
  confidence_tier: ConfidenceTierSchema,
  model_name: z.string(),
  model_version: z.string(),
});

export const ReviewDecisionEntrySchema = z.object({
  id: z.string(),
  review_task_id: z.string(),
  reviewer_id: z.string(),
  decision: ReviewDecisionSchema,
  /** Present only on a correction. Never edits the prediction it sits beside. */
  corrected_labels: z
    .object({
      stance: StanceSchema.optional(),
      hate_types: z.array(HateTypeSchema).optional(),
      severity: z.number().int().min(0).max(3).optional(),
    })
    .nullable(),
  note: z.string().nullable(),
  is_training_candidate: z.boolean(),
  created_at: z.string(),
});

/**
 * A decision to append.
 *
 * The correction pairing is a rule the service enforces and the schema states:
 * a correction must carry corrected labels, and only a correction may. The
 * training flag is a quarantine marker, allowed on corrections alone; nothing
 * retrains a model from it.
 */
export const AppendDecisionRequestSchema = z
  .object({
    decision: ReviewDecisionSchema,
    note: z.string().max(2000).optional(),
    corrected_labels: z
      .object({
        stance: StanceSchema.optional(),
        hate_types: z.array(HateTypeSchema).optional(),
        severity: z.number().int().min(0).max(3).optional(),
      })
      .optional(),
    is_training_candidate: z.boolean(),
  })
  .refine((value) => (value.decision === 'corrected') === (value.corrected_labels !== undefined), {
    message: 'a correction must carry corrected labels, and only a correction may',
    path: ['corrected_labels'],
  })
  .refine((value) => !value.is_training_candidate || value.decision === 'corrected', {
    message: 'only a correction may be marked as a training candidate',
    path: ['is_training_candidate'],
  });

export const ReviewTaskDetailSchema = z.object({
  task: ReviewTaskSchema,
  decisions: z.array(ReviewDecisionEntrySchema),
});

export const ReviewQueuePageSchema = z.object({
  items: z.array(ReviewTaskSchema),
  next_cursor: z.string().nullable(),
  /** Counts for the queue as a whole, so a figure never rests on one page. */
  totals: z.object({
    open: z.number().int().nonnegative(),
    decided: z.number().int().nonnegative(),
    confirmed: z.number().int().nonnegative(),
    classified_in_window: z.number().int().nonnegative(),
  }),
});

export type ReviewTaskType = z.infer<typeof ReviewTaskTypeSchema>;
export type ReviewTaskStatus = z.infer<typeof ReviewTaskStatusSchema>;
export type ReviewDecisionKind = z.infer<typeof ReviewDecisionSchema>;
export type ReviewTask = z.infer<typeof ReviewTaskSchema>;
export type ReviewDecisionEntry = z.infer<typeof ReviewDecisionEntrySchema>;
export type AppendDecisionRequest = z.infer<typeof AppendDecisionRequestSchema>;
export type ReviewTaskDetail = z.infer<typeof ReviewTaskDetailSchema>;
export type ReviewQueuePage = z.infer<typeof ReviewQueuePageSchema>;

export type HateType = z.infer<typeof HateTypeSchema>;
export type Stance = z.infer<typeof StanceSchema>;
export type Relevance = z.infer<typeof RelevanceSchema>;
export type ConfidenceTier = z.infer<typeof ConfidenceTierSchema>;
export type EvidenceClassifyRequest = z.infer<typeof EvidenceClassifyRequestSchema>;
export type ImageUpload = z.infer<typeof ImageUploadSchema>;
export type DatasetAnnotation = z.infer<typeof DatasetAnnotationSchema>;
export type ImageClassification = z.infer<typeof ImageClassificationSchema>;
export type ImageExample = z.infer<typeof ImageExampleSchema>;
export type ImageExampleList = z.infer<typeof ImageExampleListSchema>;
