/**
 * Local constants behind the Connections mockup.
 *
 * No field here holds a credential, and none holds a placeholder shaped like
 * one: a connector either says it is configured or says it is not, and that is
 * the whole of what this page needs to know. The live version reads
 * `GET /v1/admin/connections`, which is specified to be secret-free for the same
 * reason.
 */

import type { StatusIndicator } from '@/components/ui/StatusPill';

export interface Connector {
  readonly id: string;
  readonly name: string;
  readonly indicator: StatusIndicator;
  /** Status in words. The pill repeats it with a glyph and a colour. */
  readonly statusLabel: string;
  /** The documented API or permitted feed. There is no scraping fallback. */
  readonly authorisation: string;
  readonly collects: string;
  /** Null when no run has ever succeeded, which is not the same as zero items. */
  readonly lastSuccessfulRun: string | null;
  /** Days collected out of the last seven, so a gap cannot read as a quiet week. */
  readonly daysCollected: number | null;
  readonly itemsLastWeek: number | null;
  /** Why there is no figure, when there is none. Never substituted with a zero. */
  readonly gapReason: string | null;
  /** What a reader must know before trusting this connector's contribution. */
  readonly caveat: string;
}

export const CONNECTORS: readonly Connector[] = [
  {
    id: 'youtube',
    name: 'YouTube Data API',
    indicator: 'ok',
    statusLabel: 'Connected',
    authorisation: 'YouTube Data API v3, key-based, quota-bounded',
    collects: 'Comment threads on a named list of public videos, plus video titles for context.',
    lastSuccessfulRun: '22 August 2026, 16:05 UTC',
    daysCollected: 7,
    itemsLastWeek: 4182,
    gapReason: null,
    caveat:
      'Quota caps the run, so a busy video is sampled rather than read in full. The sample is bounded by quota, not chosen to be representative.',
  },
  {
    id: 'reddit',
    name: 'Reddit API',
    indicator: 'blocked',
    statusLabel: 'Access required',
    authorisation: 'Reddit for Researchers, application pending. No scraping fallback exists.',
    collects: 'Nothing yet. Comments on named public threads once research access is granted.',
    lastSuccessfulRun: null,
    daysCollected: null,
    itemsLastWeek: null,
    gapReason: 'Research access has not been granted, so there is nothing to count.',
    caveat:
      'Reddit is absent from every figure in the workspace. That absence is a gap in coverage, not evidence that Reddit is quiet.',
  },
  {
    id: 'bluesky',
    name: 'Bluesky',
    indicator: 'ok',
    statusLabel: 'Connected',
    authorisation: 'Public AT Protocol app view, read-only',
    collects: 'Replies to a named list of public posts, and their post text.',
    lastSuccessfulRun: '22 August 2026, 15:48 UTC',
    daysCollected: 7,
    itemsLastWeek: 1367,
    gapReason: null,
    caveat:
      'Deleted posts stay in the record as deleted, with their content withheld, so a later reader can see that something was collected and then removed.',
  },
  {
    id: 'mastodon',
    name: 'Mastodon (single instance)',
    indicator: 'degraded',
    statusLabel: 'Degraded',
    authorisation: 'One instance, public timeline API, with the operator informed',
    collects: 'Public posts and replies on one instance only, never the wider federation.',
    lastSuccessfulRun: '19 August 2026, 03:11 UTC',
    daysCollected: 4,
    itemsLastWeek: 296,
    gapReason: null,
    caveat:
      'The instance rate-limited three of the last seven runs. Those three days are gaps and are excluded from denominators rather than counted as zero.',
  },
  {
    id: 'open-datapack',
    name: 'Open datapack import',
    indicator: 'absent',
    statusLabel: 'Not configured for scheduled runs',
    authorisation: 'Reviewed manifest, verified file hash, recorded licence',
    collects:
      'A one-off import of reviewed rows. Public platform is shown as N/A while dataset lineage is kept in full.',
    lastSuccessfulRun: '11 August 2026, 09:30 UTC',
    daysCollected: null,
    itemsLastWeek: null,
    gapReason: 'A one-off import produces no daily figure, so there is none to show.',
    caveat:
      'An import is not collection. This connector contributes historical rows and no daily figure, so the trend charts show it as absent rather than flat.',
  },
];

export interface DatapackProvenance {
  readonly datasetName: string;
  readonly provider: string;
  readonly version: string;
  readonly licence: string;
  readonly licenceUrl: string;
  /** SHA-256 of the imported file, in full. A truncated hash cannot be checked. */
  readonly fileHash: string;
  readonly rowCount: number;
  readonly rowsImported: number;
  readonly retrievedAt: string;
  readonly approvedBy: string;
  readonly annotationNote: string;
}

export const DATAPACK: DatapackProvenance = {
  datasetName: 'Public Discourse Hate Speech Annotations (synthetic stand-in)',
  provider: 'Open research catalogue',
  version: 'v2.1, revision 2026-05-04',
  licence: 'CC BY 4.0',
  licenceUrl: 'https://creativecommons.org/licenses/by/4.0/',
  fileHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  rowCount: 41382,
  rowsImported: 40917,
  retrievedAt: '11 August 2026, 09:12 UTC',
  approvedBy: 'Licence reviewed and approved before import',
  annotationNote:
    'The dataset ships its own labels. They are stored as original dataset annotations, not as Amanah predictions and not as human review decisions.',
};
