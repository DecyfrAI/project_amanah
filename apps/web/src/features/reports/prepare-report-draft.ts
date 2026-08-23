/**
 * Deterministic F-S14 draft builder.
 *
 * This is the mock "model": it never OCRs a screenshot, never calls a vision
 * API, and never contacts Reddit or YouTube. It fills a platform template from
 * the selected platform, the reporter's own note, and, when no note is typed,
 * a milder synthetic fixture line quoted in full.
 */
import type { ReportDraft, ReportDraftRequest, ReportPlatform } from '@/api/contracts';

/** Same milder synthetic line as the marketing feed. Quoted in full, never redacted. */
export const FIXTURE_QUOTE = "They don't belong here. There are other places they can go.";

export interface PlatformReportCatalog {
  readonly id: ReportPlatform;
  readonly label: string;
  readonly to: string;
  readonly toNote: string;
  readonly policyUrl: string | null;
  readonly policyLabel: string | null;
  readonly officialReportUrl: string | null;
  readonly officialReportLabel: string | null;
  readonly subject: string;
}

export const PLATFORM_REPORT_CATALOG: Record<ReportPlatform, PlatformReportCatalog> = {
  youtube: {
    id: 'youtube',
    label: 'YouTube',
    to: 'report@youtube.example',
    toNote:
      'YouTube does not publish a public mailbox for ordinary hate or harassment reports. Use Report on the video or comment, then paste this wording into the official reporting help page.',
    policyUrl: 'https://support.google.com/youtube/answer/2801939',
    policyLabel: 'YouTube hate speech policy',
    officialReportUrl: 'https://support.google.com/youtube/answer/2802027',
    officialReportLabel: 'YouTube reporting help',
    subject: 'Request for review: possible hate or harassment on YouTube',
  },
  reddit: {
    id: 'reddit',
    label: 'Reddit',
    to: 'report@reddit.example',
    toNote:
      'Reddit does not publish a public mailbox for ordinary Content Policy reports. Paste this wording into the official report form, or use Report on the post or comment. Do not send an ordinary content report to Reddit Legal.',
    policyUrl: 'https://www.redditinc.com/policies/content-policy',
    policyLabel: 'Reddit Rules (content policy)',
    officialReportUrl: 'https://www.reddit.com/report',
    officialReportLabel: 'Reddit official report form',
    subject: 'Request for review: possible hate or harassment on Reddit',
  },
  other: {
    id: 'other',
    label: 'Other platform',
    to: 'report@platform.example',
    toNote:
      'Placeholder address for fixture mode. Live mode will use a backend allow-list for the platform the reporter named. This is not a government address.',
    policyUrl: null,
    policyLabel: null,
    officialReportUrl: null,
    officialReportLabel: null,
    subject: 'Request for review: possible hate or harassment on a hosted platform',
  },
};

export const REPORT_PLATFORM_OPTIONS: readonly { id: ReportPlatform; label: string }[] = [
  { id: 'youtube', label: 'YouTube' },
  { id: 'reddit', label: 'Reddit' },
  { id: 'other', label: 'Other platform' },
];

export function isReportPlatform(value: string): value is ReportPlatform {
  return value === 'youtube' || value === 'reddit' || value === 'other';
}

export function reportPlatformFromLabel(label: string): ReportPlatform {
  const normalised = label.trim().toLowerCase();
  if (normalised === 'youtube' || normalised === 'reddit') {
    return normalised;
  }
  return 'other';
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} bytes`;
  }
  return `${Math.round(size / 1024)} KB`;
}

function quoteForDraft(input: ReportDraftRequest): string {
  const note = input.reporter_note?.trim() ?? '';
  if (note.length > 0) {
    return note;
  }
  return FIXTURE_QUOTE;
}

function imageLine(input: ReportDraftRequest): string {
  if (!input.has_image) {
    return 'Screenshot: none. The reporter described what they saw in writing, or asked for a draft without an image.';
  }
  const name = input.image_filename ?? 'an image';
  const size =
    input.image_byte_size === undefined ? 'size not recorded' : formatBytes(input.image_byte_size);
  return `Screenshot: the sender will attach ${name} (${size}) from their own device. Amanah did not receive the file and did not OCR it.`;
}

function buildBody(
  input: ReportDraftRequest,
  catalog: PlatformReportCatalog,
  quote: string,
): string {
  const urlLine =
    input.content_url === undefined
      ? 'Content URL: not provided.'
      : `Content URL (typed by the reporter, not fetched): ${input.content_url}`;
  const itemLine =
    input.source_item_id === undefined
      ? null
      : `Content reference in Amanah: ${input.source_item_id}. That identifies collected content, not a person.`;

  const lines: readonly (string | null)[] = [
    'This is a prepared report for a person to send. Amanah has not sent it.',
    'It is not a confirmed finding that the content is hate.',
    '',
    'This prepares a platform report. It does not notify a government authority.',
    `It is formatted for the official ${catalog.label} report form, not for an email inbox and not for law enforcement.`,
    '',
    `Platform: ${catalog.label}`,
    urlLine,
    imageLine(input),
    itemLine,
    '',
    'Quoted wording (as provided, or a fixture transcription when none was typed):',
    quote,
    '',
    `Why this may warrant a review: the reporter is asking ${catalog.label} to review this content against its hate and harassment policies. A model prepared this wording from the selected platform and from the text above. It is classified as likely needing a platform review only because a person chose to prepare a report. That is not a finding that the comment is hate.`,
    '',
    'Request: please review the content and take the action your policies provide.',
    '',
    'Prepare one report for content you saw. Do not organise mass duplicate reports.',
    '',
    'Prepared by Project Amanah. Model-prepared draft, not sent, not a confirmed finding.',
  ];

  return lines.filter((line): line is string => line !== null).join('\n');
}

/**
 * Builds a prepared email. Filename and size may shape the evidence line.
 * Pixel data is never an input.
 */
export function prepareReportDraft(
  input: ReportDraftRequest,
  dataMode: ReportDraft['data_mode'] = 'fixture',
): ReportDraft {
  const catalog = PLATFORM_REPORT_CATALOG[input.platform];
  const quote = quoteForDraft(input);
  const confidence = input.has_image ? 0.41 : 0.28;

  return {
    data_mode: dataMode,
    platform: catalog.id,
    platform_label: catalog.label,
    to: catalog.to,
    to_kind: 'placeholder',
    to_note: catalog.toNote,
    official_report_url: catalog.officialReportUrl,
    official_report_label: catalog.officialReportLabel,
    subject: catalog.subject,
    body: buildBody(input, catalog, quote),
    likely_quote: quote,
    platform_guess: input.platform,
    confidence,
    model_name: 'amanah-report-stub',
    model_version: 'fixture-0.1',
    status: 'prepared_not_sent',
    disclosure:
      'Model-prepared draft, not sent, not a confirmed finding. The stub read the selected platform, the optional note, and image filename or size only.',
  };
}
