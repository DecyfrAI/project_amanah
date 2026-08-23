import { useCallback, useState } from 'react';

import type { ReportDraft } from '@/api';
import { StatusPill } from '@/components/ui/StatusPill';

import { downloadText } from './report-export';

import styles from './ReportDraftPreview.module.css';

interface ReportDraftPreviewProps {
  readonly draft: ReportDraft;
}

function filenameStub(platform: string): string {
  return `amanah-${platform}-report`;
}

/**
 * Prepared report wording and human-only copy actions. F-S14.
 *
 * Copy and download are initiated by the reader. Nothing here opens a mail
 * app or submits the report to a platform. YouTube and Reddit take ordinary
 * reports through forms, not a public mailbox.
 */
export function ReportDraftPreview({ draft }: ReportDraftPreviewProps) {
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const copy = useCallback(async (label: string, text: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus(label);
    } catch {
      setCopyStatus('Copy is unavailable in this browser. Select the text and copy it yourself.');
    }
  }, []);

  const handleCopyBody = useCallback((): void => {
    void copy('Copied the report wording.', draft.body);
  }, [copy, draft.body]);

  const handleDownloadTxt = useCallback((): void => {
    downloadText(`${filenameStub(draft.platform)}.txt`, draft.body, 'text/plain');
  }, [draft]);

  return (
    <div className={styles.preview}>
      <div className={styles.previewHead}>
        <h3 className={styles.previewTitle}>Prepared report wording</h3>
        <StatusPill indicator="pending" label="Prepared, not sent" />
      </div>
      <p className={styles.disclosure}>{draft.disclosure}</p>
      <p className={styles.note}>{draft.to_note}</p>
      <p className={styles.authority}>
        This prepares a platform report. It does not notify a government authority. Paste the
        wording into the official form. Amanah does not email a platform for you.
      </p>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="draft-body">
          Wording to paste
        </label>
        <textarea className={styles.body} id="draft-body" readOnly rows={16} value={draft.body} />
      </div>

      <p className={styles.model}>
        {draft.model_name} {draft.model_version}. Model score {draft.confidence.toFixed(2)}, not a
        measure of certainty. Quoted wording is shown in full.
      </p>

      <div className={styles.actions}>
        <button type="button" className={styles.action} onClick={handleCopyBody}>
          Copy wording
        </button>
        <button type="button" className={styles.action} onClick={handleDownloadTxt}>
          Download .txt
        </button>
      </div>
      {copyStatus !== null && <output className={styles.copyStatus}>{copyStatus}</output>}

      {draft.official_report_url !== null && draft.official_report_label !== null && (
        <p className={styles.official}>
          <a href={draft.official_report_url} rel="noreferrer noopener" target="_blank">
            {draft.official_report_label} (opens in a new tab)
          </a>
          . Paste the wording there. Amanah does not submit that form for you.
        </p>
      )}
    </div>
  );
}
