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
  containersMonitored: z.number().int().nonnegative(),
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
  available: DateWindowSchema,
  defaultWindowDays: z.number().int().positive(),
  platforms: z.array(FilterOptionSchema),
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

export const ExplorerItemSchema = z.object({
  id: z.string(),
  date: z.string(),
  platform: z.string(),
  containerTitle: z.string(),
  containerUrl: z.string(),
  redactedExcerpt: z.string(),
  relevance: z.enum(['muslim_related', 'not_related']),
  classification: z.enum(['likely_hate', 'not_hate']),
  hateType: z.string().nullable(),
  severity: z.number().int().min(0).max(3).nullable(),
  /** Model score, never described to a reader as certainty. */
  modelScore: z.number().min(0).max(1),
  reviewState: z.enum(['pending', 'confirmed', 'corrected']),
  reviewNote: z.string().nullable(),
  image: ExplorerItemImageSchema.nullable().optional(),
});

export const ExplorerPageSchema = z.object({
  applied: AppliedFiltersSchema,
  matched: z.number().int().nonnegative(),
  returned: z.number().int().nonnegative(),
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
  published_at: z.string(),
  retrieved_at: z.string(),
  language: z.string(),
  scope: z.enum(['local', 'global']),
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
export type ExplorerItem = z.infer<typeof ExplorerItemSchema>;
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
});

export const DatasetAnnotationSchema = z.object({
  hate_types: z.array(HateTypeSchema).min(1),
  severity: z.number().int().min(0).max(3),
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
  image_src: z.string(),
  alt_text: z.string().min(1),
  form_note: z.string(),
  dataset_annotation: DatasetAnnotationSchema,
  score: z.number().min(0).max(1),
  narrative_tags: z.array(z.string()),
  rationale: z.string(),
});

export const ImageExampleListSchema = z.object({
  data_mode: z.enum(['fixture', 'live', 'fallback', 'stale', 'unavailable']),
  manifest: z.object({
    dataset_provider: z.string(),
    dataset_name: z.string(),
    dataset_version: z.string(),
    license_identifier: z.string(),
    schema_mapping_version: z.string(),
    approval_state: z.string(),
    reviewer: z.string(),
  }),
  items: z.array(ImageExampleSchema),
});

export type HateType = z.infer<typeof HateTypeSchema>;
export type Stance = z.infer<typeof StanceSchema>;
export type ConfidenceTier = z.infer<typeof ConfidenceTierSchema>;
export type EvidenceClassifyRequest = z.infer<typeof EvidenceClassifyRequestSchema>;
export type DatasetAnnotation = z.infer<typeof DatasetAnnotationSchema>;
export type ImageClassification = z.infer<typeof ImageClassificationSchema>;
export type ImageExample = z.infer<typeof ImageExampleSchema>;
export type ImageExampleList = z.infer<typeof ImageExampleListSchema>;
