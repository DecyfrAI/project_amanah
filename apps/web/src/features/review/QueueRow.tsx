import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import {
  ApiRequestError,
  type HateType,
  type ReviewDecisionEntry,
  type ReviewDecisionKind,
  type ReviewTask,
  type Stance,
} from '@/api';
import { StatusPill } from '@/components/ui/StatusPill';
import { reportPlatformFromLabel } from '@/features/reports/prepare-report-draft';

import {
  HATE_TYPE_LABELS,
  PLATFORM_LABELS,
  SEVERITY_LABELS,
  STANCE_LABELS,
  TASK_TYPE_LABELS,
} from './labels';
import { useAppendDecision, useClaimReviewTask } from './useReviewQueue';

import styles from './QueueRow.module.css';

interface QueueRowProps {
  task: ReviewTask;
  decisions: readonly ReviewDecisionEntry[];
  onDecided: (detail: { task: ReviewTask; decisions: readonly ReviewDecisionEntry[] }) => void;
}

function formatObserved(timestamp: string): string {
  return new Date(timestamp).toISOString().replace('T', ' ').slice(0, 16).concat(' UTC');
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'That decision could not be recorded. Try again.';
}

const STANCE_OPTIONS: readonly Stance[] = [
  'likely_anti_muslim',
  'non_hateful_discussion',
  'counterspeech_or_quotation',
  'uncertain',
];

const HATE_TYPE_OPTIONS: readonly HateType[] = [
  'animosity',
  'derogation',
  'dehumanization',
  'exclusion',
  'threat_or_incitement',
  'collective_blame',
  'other',
];

/**
 * One item awaiting a decision.
 *
 * A decision appends beside the model's proposal rather than replacing it, so
 * the proposed label stays on screen after a reviewer disagrees with it. The
 * excerpt is synthetic wording shown in full. The severity band is deliberately
 * plain text, since brand system 4 reserves red for harm a person has confirmed.
 */
export function QueueRow({ task, decisions, onDecided }: QueueRowProps) {
  const headingId = `${task.id}-container`;
  const claim = useClaimReviewTask();
  const append = useAppendDecision();
  const [correcting, setCorrecting] = useState(false);
  const [note, setNote] = useState('');
  const [stance, setStance] = useState<Stance>(task.stance);
  const [severity, setSeverity] = useState<number>(task.severity);
  const [hateTypes, setHateTypes] = useState<readonly HateType[]>(task.hate_types);
  const [isTrainingCandidate, setIsTrainingCandidate] = useState(false);

  const isMine = task.status === 'claimed' && task.assigned_to !== null;
  const isSettled = task.status === 'completed';

  const handleClaim = useCallback((): void => {
    claim.mutate(task.id, { onSuccess: onDecided });
  }, [claim, onDecided, task.id]);

  const decide = useCallback(
    (decision: ReviewDecisionKind): void => {
      append.mutate(
        {
          taskId: task.id,
          input: {
            decision,
            ...(note.trim() === '' ? {} : { note: note.trim() }),
            ...(decision === 'corrected'
              ? { corrected_labels: { stance, hate_types: [...hateTypes], severity } }
              : {}),
            is_training_candidate: decision === 'corrected' && isTrainingCandidate,
          },
        },
        {
          onSuccess: (detail) => {
            setCorrecting(false);
            setNote('');
            onDecided(detail);
          },
        },
      );
    },
    [append, hateTypes, isTrainingCandidate, note, onDecided, severity, stance, task.id],
  );

  const handleConfirm = useCallback((): void => {
    decide('confirmed');
  }, [decide]);

  const handleNeedsContext = useCallback((): void => {
    decide('needs_context');
  }, [decide]);

  const handleSubmitCorrection = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      decide('corrected');
    },
    [decide],
  );

  const handleStartCorrection = useCallback((): void => {
    setCorrecting(true);
  }, []);

  const handleCancelCorrection = useCallback((): void => {
    setCorrecting(false);
  }, []);

  const handleNoteChange = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setNote(event.currentTarget.value);
  }, []);

  const handleStanceChange = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    setStance(event.currentTarget.value as Stance);
  }, []);

  const handleSeverityChange = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    setSeverity(Number(event.currentTarget.value));
  }, []);

  const handleTrainingChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setIsTrainingCandidate(event.currentTarget.checked);
  }, []);

  const toggleHateType = useCallback((type: HateType): void => {
    setHateTypes((current) =>
      current.includes(type) ? current.filter((entry) => entry !== type) : [...current, type],
    );
  }, []);

  const pending = claim.isPending || append.isPending;

  return (
    <li className={styles.row}>
      <article aria-labelledby={headingId}>
        <div className={styles.top}>
          <div className={styles.identity}>
            <h3 id={headingId} className={styles.container}>
              {task.title ?? 'Untitled container'}
            </h3>
            <p className={styles.meta}>
              {PLATFORM_LABELS[task.platform] ?? task.platform} · item {task.content_item_id} ·
              observed {formatObserved(task.created_at)}
            </p>
          </div>
          <StatusPill
            indicator={isSettled ? 'ok' : 'pending'}
            label={isSettled ? 'Decided' : isMine ? 'Claimed by you' : 'Awaiting review'}
          />
        </div>

        <dl className={styles.facts}>
          <div className={styles.fact}>
            <dt className={styles.term}>Proposed label</dt>
            <dd className={styles.value}>{STANCE_LABELS[task.stance]}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Model score</dt>
            <dd className={styles.value}>
              {task.score.toFixed(2)} ({task.confidence_tier} confidence)
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Severity band</dt>
            <dd className={styles.value}>
              {task.severity} of 3, {SEVERITY_LABELS[task.severity]}
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Why it is queued</dt>
            <dd className={styles.value}>{TASK_TYPE_LABELS[task.task_type]}</dd>
          </div>
        </dl>

        <div className={styles.excerptBlock}>
          <p className={styles.excerpt}>{task.permitted_excerpt ?? 'No excerpt was stored.'}</p>
        </div>

        {decisions.length > 0 && (
          <ol className={styles.decisions}>
            {decisions.map((entry) => (
              <li key={entry.id} className={styles.decision}>
                <p className={styles.decisionHead}>
                  {DECISION_LABELS[entry.decision]} · {formatObserved(entry.created_at)}
                </p>
                {entry.corrected_labels !== null && (
                  <p className={styles.decisionDetail}>
                    Corrected to {STANCE_LABELS[entry.corrected_labels.stance ?? task.stance]},
                    severity {entry.corrected_labels.severity ?? task.severity}
                    {(entry.corrected_labels.hate_types ?? []).length > 0
                      ? `, ${(entry.corrected_labels.hate_types ?? [])
                          .map((type) => HATE_TYPE_LABELS[type])
                          .join(', ')}`
                      : ''}
                    . The model's proposal above is unchanged.
                  </p>
                )}
                {entry.note !== null && <p className={styles.decisionNote}>{entry.note}</p>}
                {entry.is_training_candidate && (
                  <p className={styles.decisionDetail}>
                    Flagged for the training-candidate pool. Nothing retrains a model from it.
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}

        {!isSettled && (
          <div className={styles.actions}>
            {!isMine ? (
              <>
                <button
                  type="button"
                  className={styles.primaryAction}
                  onClick={handleClaim}
                  disabled={pending}
                >
                  {claim.isPending ? 'Claiming…' : 'Claim to review'}
                </button>
                <p className={styles.actionNote}>
                  A claim is a lease for 30 minutes, so two reviewers cannot decide the same item.
                </p>
              </>
            ) : correcting ? (
              <form className={styles.correction} onSubmit={handleSubmitCorrection}>
                <p className={styles.correctionLead}>
                  A correction is appended beside the model's proposal. It never edits it.
                </p>

                <div className={styles.field}>
                  <label className={styles.label} htmlFor={`${task.id}-stance`}>
                    Corrected stance
                  </label>
                  <select
                    id={`${task.id}-stance`}
                    className={styles.control}
                    value={stance}
                    onChange={handleStanceChange}
                  >
                    {STANCE_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {STANCE_LABELS[option]}
                      </option>
                    ))}
                  </select>
                </div>

                <div className={styles.field}>
                  <label className={styles.label} htmlFor={`${task.id}-severity`}>
                    Corrected severity
                  </label>
                  <select
                    id={`${task.id}-severity`}
                    className={styles.control}
                    value={severity}
                    onChange={handleSeverityChange}
                  >
                    {[0, 1, 2, 3].map((band) => (
                      <option key={band} value={band}>
                        {band} of 3, {SEVERITY_LABELS[band]}
                      </option>
                    ))}
                  </select>
                </div>

                <fieldset className={styles.fieldset}>
                  <legend className={styles.label}>Corrected hate types</legend>
                  <div className={styles.checkboxes}>
                    {HATE_TYPE_OPTIONS.map((type) => (
                      <HateTypeCheckbox
                        key={type}
                        taskId={task.id}
                        type={type}
                        checked={hateTypes.includes(type)}
                        onToggle={toggleHateType}
                      />
                    ))}
                  </div>
                </fieldset>

                <label className={styles.checkboxRow}>
                  <input
                    type="checkbox"
                    checked={isTrainingCandidate}
                    onChange={handleTrainingChange}
                  />
                  <span>
                    Flag for the training-candidate pool. A quarantine marker only: nothing retrains
                    or activates a model from it.
                  </span>
                </label>

                <div className={styles.correctionActions}>
                  <button type="submit" className={styles.primaryAction} disabled={pending}>
                    {append.isPending ? 'Recording…' : 'Record correction'}
                  </button>
                  <button
                    type="button"
                    className={styles.action}
                    onClick={handleCancelCorrection}
                    disabled={pending}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <>
                <button
                  type="button"
                  className={styles.primaryAction}
                  onClick={handleConfirm}
                  disabled={pending}
                >
                  Confirm label
                </button>
                <button
                  type="button"
                  className={styles.action}
                  onClick={handleStartCorrection}
                  disabled={pending}
                >
                  Correct label
                </button>
                <button
                  type="button"
                  className={styles.action}
                  onClick={handleNeedsContext}
                  disabled={pending}
                >
                  Needs context
                </button>
              </>
            )}

            {isMine && !correcting && (
              <div className={styles.field}>
                <label className={styles.label} htmlFor={`${task.id}-note`}>
                  Reviewer note (optional)
                </label>
                <textarea
                  id={`${task.id}-note`}
                  className={styles.control}
                  value={note}
                  onChange={handleNoteChange}
                  rows={2}
                  maxLength={2000}
                />
                <p className={styles.actionNote}>
                  Internal. A disputing user sees a composed summary, never this text.
                </p>
              </div>
            )}

            {(claim.isError || append.isError) && (
              <p className={styles.error} role="alert">
                {errorMessage(claim.error ?? append.error)}
              </p>
            )}
          </div>
        )}

        <p className={styles.reportCue}>
          If this content should go to a platform, prepare a report. That opens Reports. It does not
          send anything, and it is not a review decision.
        </p>
        <Link
          className={styles.reportLink}
          to={`/app/reports?platform=${reportPlatformFromLabel(PLATFORM_LABELS[task.platform] ?? task.platform)}&item=${encodeURIComponent(task.content_item_id)}`}
        >
          Prepare a report
        </Link>

        <p className={styles.provenance}>
          {task.model_name} {task.model_version}
        </p>
      </article>
    </li>
  );
}

const DECISION_LABELS: Record<ReviewDecisionKind, string> = {
  confirmed: 'Confirmed the proposed label',
  corrected: 'Corrected the proposed label',
  needs_context: 'Returned to the queue for context',
  rejected: 'Rejected the proposed label',
};

interface HateTypeCheckboxProps {
  readonly taskId: string;
  readonly type: HateType;
  readonly checked: boolean;
  readonly onToggle: (type: HateType) => void;
}

function HateTypeCheckbox({ taskId, type, checked, onToggle }: HateTypeCheckboxProps) {
  const handleChange = useCallback((): void => {
    onToggle(type);
  }, [onToggle, type]);

  return (
    <label className={styles.checkboxRow} htmlFor={`${taskId}-${type}`}>
      <input id={`${taskId}-${type}`} type="checkbox" checked={checked} onChange={handleChange} />
      <span>{HATE_TYPE_LABELS[type]}</span>
    </label>
  );
}
