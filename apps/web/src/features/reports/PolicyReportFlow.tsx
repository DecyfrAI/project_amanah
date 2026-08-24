import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ApiRequestError, type WirePolicyCandidate, type WirePreparedReport } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';

import {
  useAnalyzePolicies,
  useRecordReportOutcome,
  useSavePreparedReport,
} from './usePolicyReport';

import styles from './PolicyReportFlow.module.css';

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return fallback;
}

const OUTCOMES = [
  { value: 'no_response', label: 'No response from the platform' },
  { value: 'content_removed', label: 'Content was removed' },
  { value: 'content_restricted', label: 'Content was restricted' },
  { value: 'no_violation', label: 'Platform found no violation' },
  { value: 'other', label: 'Something else' },
] as const;

/**
 * Assisted platform reporting through the reviewed policy catalogue
 * (spec §9.9, B-S18, completion guide step 6).
 *
 * The person names an item, reads the possible policy matches with their
 * official links and versions, explicitly confirms one, reviews the bounded
 * evidence summary and suggested wording, and saves the record. Amanah never
 * submits anything: there is no client in this flow that could, and the saved
 * status distinguishes what the user prepared from what the user says they
 * filed.
 */
export function PolicyReportFlow() {
  const [params] = useSearchParams();
  const analyze = useAnalyzePolicies();
  const save = useSavePreparedReport();
  const outcome = useRecordReportOutcome();

  const [itemId, setItemId] = useState(params.get('item') ?? '');
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [evidenceSummary, setEvidenceSummary] = useState('');
  const [suggestedText, setSuggestedText] = useState('');
  const [draftSubject, setDraftSubject] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const candidates = analyze.data?.candidates ?? [];
  const selected =
    candidates.find((entry) => entry.platform_policy_id === selectedPolicyId) ?? null;
  const saved = save.data;

  const handleItemId = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setItemId(event.currentTarget.value);
    setFormError(null);
  }, []);

  const handleAnalyze = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      const trimmed = itemId.trim();
      if (trimmed === '') {
        setFormError('Enter the item reference you want to report.');
        return;
      }
      setSelectedPolicyId(null);
      setConfirmed(false);
      save.reset();
      analyze.mutate(trimmed);
    },
    [analyze, itemId, save],
  );

  const handleSelectPolicy = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setSelectedPolicyId(event.currentTarget.value);
    // Choosing a different rule invalidates the previous confirmation: the
    // person must confirm the rule they actually intend to report under.
    setConfirmed(false);
  }, []);

  const handleConfirm = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setConfirmed(event.currentTarget.checked);
  }, []);

  const handleEvidenceSummary = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setEvidenceSummary(event.currentTarget.value);
  }, []);

  const handleSuggestedText = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setSuggestedText(event.currentTarget.value);
  }, []);

  const handleDraftSubject = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setDraftSubject(event.currentTarget.value);
  }, []);

  const handleSave = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      if (selected === null || !confirmed) {
        setFormError('Choose a policy and confirm the version you read.');
        return;
      }
      if (evidenceSummary.trim() === '' || suggestedText.trim() === '') {
        setFormError('Write both the evidence summary and the wording you would send.');
        return;
      }
      const needsSubject = selected.recipient_kind === 'allowlist_email';
      if (needsSubject && draftSubject.trim() === '') {
        setFormError('This platform has no official form, so the draft needs a subject line.');
        return;
      }
      setFormError(null);
      save.mutate({
        contentItemId: itemId.trim(),
        platformPolicyId: selected.platform_policy_id,
        policyVersion: selected.version,
        evidenceSummary: evidenceSummary.trim(),
        suggestedText: suggestedText.trim(),
        ...(needsSubject ? { draftSubject: draftSubject.trim() } : {}),
      });
    },
    [confirmed, draftSubject, evidenceSummary, itemId, save, selected, suggestedText],
  );

  return (
    <section className={styles.card} aria-labelledby="policy-report-heading">
      <div className={styles.headingRow}>
        <h2 id="policy-report-heading" className={styles.sectionHeading}>
          Report against a platform policy
        </h2>
        <InfoTip label="Report against a platform policy">
          Amanah shows the platform&apos;s own reviewed rules, with links and versions, so you can
          decide which one applies. It never submits a report and never claims a platform received
          one.
        </InfoTip>
      </div>
      <p className={styles.lead}>
        Name a classified item, read the possible policy matches, confirm the rule you are reporting
        under, then save your preparation. You file the report yourself on the platform&apos;s own
        form.
      </p>

      <form onSubmit={handleAnalyze}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="policy-item">
            Item reference
          </label>
          <input
            className={styles.control}
            id="policy-item"
            name="policy-item"
            type="text"
            value={itemId}
            onChange={handleItemId}
            aria-describedby="policy-item-hint"
          />
          <p className={styles.hint} id="policy-item-hint">
            A content reference from Explorer or Review. It is not a person.
          </p>
        </div>
        <button type="submit" className={styles.action} disabled={analyze.isPending}>
          {analyze.isPending ? 'Reading the catalogue…' : 'Find matching policies'}
        </button>
      </form>

      {analyze.isError && (
        <p className={styles.error} role="alert">
          {errorMessage(analyze.error, 'The policy catalogue could not be read. Try again.')}
        </p>
      )}

      {analyze.isSuccess && candidates.length === 0 && (
        <p className={styles.disclosure}>
          No policy candidate was offered for this item. That is deliberate: Amanah does not suggest
          a rule for counterspeech, a quotation, or neutral reporting, because doing so would turn
          this into a way to report people for discussing the subject.
        </p>
      )}

      {analyze.isSuccess && candidates.length > 0 && (
        <>
          <p className={styles.disclosure}>{analyze.data.disclosure}</p>
          <form onSubmit={handleSave}>
            <fieldset>
              <legend className={styles.label}>Possible policy matches</legend>
              <ul className={styles.candidates}>
                {candidates.map((candidate) => (
                  <li key={candidate.platform_policy_id}>
                    <PolicyOption
                      candidate={candidate}
                      isSelected={candidate.platform_policy_id === selectedPolicyId}
                      onSelect={handleSelectPolicy}
                    />
                  </li>
                ))}
              </ul>
            </fieldset>

            {selected !== null && (
              <>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="evidence-summary">
                    Evidence summary
                  </label>
                  <textarea
                    className={styles.textarea}
                    id="evidence-summary"
                    name="evidence-summary"
                    value={evidenceSummary}
                    onChange={handleEvidenceSummary}
                    maxLength={4000}
                  />
                </div>

                <div className={styles.field}>
                  <label className={styles.label} htmlFor="suggested-text">
                    Wording you would send
                  </label>
                  <textarea
                    className={styles.textarea}
                    id="suggested-text"
                    name="suggested-text"
                    value={suggestedText}
                    onChange={handleSuggestedText}
                    maxLength={4000}
                  />
                </div>

                {selected.recipient_kind === 'allowlist_email' && (
                  <div className={styles.field}>
                    <label className={styles.label} htmlFor="draft-subject">
                      Subject line
                    </label>
                    <input
                      className={styles.control}
                      id="draft-subject"
                      name="draft-subject"
                      type="text"
                      value={draftSubject}
                      onChange={handleDraftSubject}
                      maxLength={300}
                      aria-describedby="draft-subject-hint"
                    />
                    <p className={styles.hint} id="draft-subject-hint">
                      This platform publishes no official form. The recipient comes from the
                      reviewed allow-list, never from this page, and nothing is sent.
                    </p>
                  </div>
                )}

                <div className={styles.field}>
                  <label className={styles.label} htmlFor="confirm-policy">
                    <input
                      id="confirm-policy"
                      name="confirm-policy"
                      type="checkbox"
                      checked={confirmed}
                      onChange={handleConfirm}
                    />{' '}
                    I read {selected.title} (version {selected.version}) and it is the rule I am
                    reporting under
                  </label>
                </div>

                <button type="submit" className={styles.primaryAction} disabled={save.isPending}>
                  {save.isPending ? 'Saving…' : 'Save prepared report'}
                </button>
              </>
            )}

            {formError !== null && (
              <p className={styles.error} role="alert">
                {formError}
              </p>
            )}
            {save.isError && (
              <p className={styles.error} role="alert">
                {errorMessage(save.error, 'The report could not be saved. Try again.')}
              </p>
            )}
          </form>
        </>
      )}

      {saved !== undefined && <SavedReport report={saved} onRecord={outcome.mutate} />}
    </section>
  );
}

interface PolicyOptionProps {
  readonly candidate: WirePolicyCandidate;
  readonly isSelected: boolean;
  readonly onSelect: (event: ChangeEvent<HTMLInputElement>) => void;
}

function PolicyOption({ candidate, isSelected, onSelect }: PolicyOptionProps) {
  const reviewed =
    candidate.last_reviewed_at === null
      ? 'never reviewed'
      : `last reviewed ${candidate.last_reviewed_at.slice(0, 10)}`;

  return (
    <div className={styles.candidate}>
      <input
        type="radio"
        name="policy"
        id={candidate.platform_policy_id}
        value={candidate.platform_policy_id}
        checked={isSelected}
        onChange={onSelect}
      />
      <div className={styles.candidateBody}>
        <label className={styles.candidateTitle} htmlFor={candidate.platform_policy_id}>
          {candidate.title}
        </label>
        <p className={styles.hint}>{candidate.summary}</p>
        <p className={styles.meta}>
          {candidate.platform} · version {candidate.version} · {reviewed} · confidence{' '}
          {candidate.confidence_tier} ({candidate.score.toFixed(2)})
        </p>
        <p className={styles.hint}>{candidate.rationale}</p>
        <a
          className={styles.link}
          href={candidate.official_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Read the platform&apos;s own rule (opens in a new tab)
        </a>
        {candidate.official_report_url !== null && (
          <a
            className={styles.link}
            href={candidate.official_report_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open the official report form (opens in a new tab)
          </a>
        )}
      </div>
    </div>
  );
}

interface SavedReportProps {
  readonly report: WirePreparedReport;
  readonly onRecord: (input: {
    reportId: string;
    input: { status: 'submitted' | 'closed'; outcome?: (typeof OUTCOMES)[number]['value'] };
  }) => void;
}

function SavedReport({ report, onRecord }: SavedReportProps) {
  const handleSubmitted = useCallback((): void => {
    onRecord({ reportId: report.id, input: { status: 'submitted' } });
  }, [onRecord, report.id]);

  const handleOutcome = useCallback(
    (event: ChangeEvent<HTMLSelectElement>): void => {
      const value = event.currentTarget.value;
      if (value === '') {
        return;
      }
      onRecord({
        reportId: report.id,
        input: { status: 'closed', outcome: value as (typeof OUTCOMES)[number]['value'] },
      });
    },
    [onRecord, report.id],
  );

  return (
    <div className={styles.saved}>
      <p className={styles.label}>Saved to your contributions</p>
      <p className={styles.hint}>
        Reference {report.id} · {report.platform} · policy version {report.policy_version} · status{' '}
        {report.status}. Amanah did not submit this report and holds no platform acknowledgement.
        {report.recipient_address !== null &&
          ` The reviewed allow-list address is ${report.recipient_address}; nothing was sent to it.`}
      </p>
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.action}
          onClick={handleSubmitted}
          disabled={report.status !== 'prepared'}
        >
          I filed this myself
        </button>
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="report-outcome">
          What did the platform do?
        </label>
        <select
          className={styles.control}
          id="report-outcome"
          name="report-outcome"
          value={report.outcome ?? ''}
          onChange={handleOutcome}
        >
          <option value="">Not recorded yet</option>
          {OUTCOMES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <p className={styles.hint}>Your own account of what happened, never a platform receipt.</p>
      </div>
    </div>
  );
}
