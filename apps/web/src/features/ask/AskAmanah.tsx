import { useCallback, useRef, useState, type ChangeEvent, type FormEvent } from 'react';

import { ApiRequestError, type AssistantReply } from '@/api';
import { Button } from '@/components/ui/Button';
import { useDashboardFilters } from '@/features/dashboard/useDashboardFilters';

import { ASK_PROMPTS, type AskPrompt } from './ask-prompts';
import { useAsk } from './useAsk';

import styles from './AskAmanah.module.css';

interface Turn {
  readonly id: string;
  readonly question: string;
  readonly reply: AssistantReply | null;
  readonly error: string | null;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  return 'That question could not be answered. Try again.';
}

function scopeLabel(from?: string, to?: string, platforms: readonly string[] = []): string {
  const windowLabel =
    from !== undefined && to !== undefined ? `${from} to ${to}` : 'the default collection window';
  if (platforms.length === 0) {
    return windowLabel;
  }
  return `${windowLabel}, ${platforms.join(', ')}`;
}

/**
 * Ask Amanah, opened from the workspace chrome.
 *
 * The panel receives the filters in the address bar so a question is about the
 * same sample the reader is looking at. Replies cite stored figures. Retrieval
 * over methodology documents is named as the live path, not pretended here.
 */
export function AskAmanah() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { filters } = useDashboardFilters();
  const ask = useAsk();
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<readonly Turn[]>([]);

  const open = useCallback((): void => {
    dialogRef.current?.showModal();
  }, []);

  const close = useCallback((): void => {
    dialogRef.current?.close();
  }, []);

  const restoreFocus = useCallback((): void => {
    triggerRef.current?.focus();
  }, []);

  const reset = useCallback((): void => {
    ask.reset();
    setTurns([]);
    setQuestion('');
  }, [ask]);

  const handleQuestionChange = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setQuestion(event.currentTarget.value);
  }, []);

  const askQuestion = useCallback(
    (raw: string): void => {
      const trimmed = raw.trim();
      if (trimmed.length === 0 || ask.isPending) {
        return;
      }

      const turnId = `ask_${crypto.randomUUID()}`;
      setTurns((current) => [
        ...current,
        { id: turnId, question: trimmed, reply: null, error: null },
      ]);
      setQuestion('');

      ask.mutate(
        {
          question: trimmed,
          ...(filters.from === undefined ? {} : { from: filters.from }),
          ...(filters.to === undefined ? {} : { to: filters.to }),
          ...(filters.platforms === undefined || filters.platforms.length === 0
            ? {}
            : { platforms: [...filters.platforms] }),
          ...(filters.hateTypes === undefined || filters.hateTypes.length === 0
            ? {}
            : { hateTypes: [...filters.hateTypes] }),
          ...(filters.severityBands === undefined || filters.severityBands.length === 0
            ? {}
            : { severityBands: [...filters.severityBands] }),
          ...(filters.reviewStates === undefined || filters.reviewStates.length === 0
            ? {}
            : { reviewStates: [...filters.reviewStates] }),
        },
        {
          onSuccess: (reply) => {
            setTurns((current) =>
              current.map((turn) => (turn.id === turnId ? { ...turn, reply } : turn)),
            );
          },
          onError: (error) => {
            setTurns((current) =>
              current.map((turn) =>
                turn.id === turnId ? { ...turn, error: errorMessage(error) } : turn,
              ),
            );
          },
        },
      );
    },
    [ask, filters],
  );

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      askQuestion(question);
    },
    [askQuestion, question],
  );

  return (
    <>
      <button ref={triggerRef} type="button" className={styles.trigger} onClick={open}>
        <span className={styles.triggerIcon} aria-hidden="true">
          <AskIcon />
        </span>
        <span className="visually-hidden">Ask Amanah</span>
      </button>

      <dialog
        ref={dialogRef}
        className={styles.dialog}
        aria-labelledby="ask-heading"
        onClose={restoreFocus}
      >
        <header className={styles.header}>
          <div>
            <h2 id="ask-heading" className={styles.title}>
              Ask Amanah
            </h2>
            <p className={styles.context}>
              Context: {scopeLabel(filters.from, filters.to, filters.platforms ?? [])}. Answers cite
              stored figures for this sample. Document retrieval is not connected in this fixture.
            </p>
          </div>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={styles.close}
              onClick={reset}
              disabled={turns.length === 0 && question.length === 0}
            >
              New chat
            </button>
            <button type="button" className={styles.close} onClick={close}>
              Close
            </button>
          </div>
        </header>

        <div className={styles.thread}>
          {turns.length === 0 ? (
            <div className={styles.emptyBlock}>
              <p className={styles.empty}>
                Start from a stored figure, an Explorer entry, or coinciding news. I will not invent
                a number that is not already on the page. A live assistant can retrieve more behind
                the same questions.
              </p>
              <ul className={styles.prompts}>
                {ASK_PROMPTS.map((prompt) => (
                  <li key={prompt.id}>
                    <PromptButton disabled={ask.isPending} prompt={prompt} onAsk={askQuestion} />
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <ol className={styles.turns}>
              {turns.map((turn) => (
                <li key={turn.id} className={styles.turn}>
                  <p className={styles.question}>
                    <span className={styles.who}>You</span>
                    {turn.question}
                  </p>
                  {turn.reply !== null && <ReplyBlock reply={turn.reply} />}
                  {turn.error !== null && (
                    <p className={styles.error} role="alert">
                      {turn.error}
                    </p>
                  )}
                  {turn.reply === null && turn.error === null && <PendingBlock />}
                </li>
              ))}
            </ol>
          )}
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label} htmlFor="ask-question">
            Ask about this window
          </label>
          <textarea
            id="ask-question"
            className={styles.input}
            value={question}
            onChange={handleQuestionChange}
            rows={3}
            required
          />
          <Button variant="primary" type="submit" disabled={ask.isPending}>
            {ask.isPending ? 'Reading…' : 'Ask'}
          </Button>
        </form>
      </dialog>
    </>
  );
}

interface PromptButtonProps {
  readonly prompt: AskPrompt;
  readonly disabled: boolean;
  readonly onAsk: (question: string) => void;
}

function PromptButton({ prompt, disabled, onAsk }: PromptButtonProps) {
  const handleClick = useCallback(() => {
    onAsk(prompt.question);
  }, [onAsk, prompt.question]);

  return (
    <button type="button" className={styles.prompt} disabled={disabled} onClick={handleClick}>
      {prompt.label}
    </button>
  );
}

/**
 * Shown while a reply is in flight. The dots carry the waiting; the sentence
 * says what is being read, so the reader knows the delay is a lookup and not a
 * stall. `aria-live` announces it once for a screen reader.
 */
function PendingBlock() {
  return (
    <p className={styles.pending} aria-live="polite">
      <span className={styles.who}>Amanah</span>
      <span className={styles.dots} aria-hidden="true">
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
      </span>
      Reading the figures for this window.
    </p>
  );
}

function ReplyBlock({ reply }: { reply: AssistantReply }) {
  return (
    <div className={styles.reply}>
      <p>
        <span className={styles.who}>Amanah</span>
        {reply.answer}
      </p>
      {reply.citations.length > 0 && (
        <p className={styles.citations}>
          Cited: {reply.citations.map((citation) => citation.label).join('; ')}
        </p>
      )}
      <ul className={styles.limits}>
        {reply.limitations.map((limitation) => (
          <li key={limitation}>{limitation}</li>
        ))}
      </ul>
    </div>
  );
}

function AskIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M5 6.5h14v9.5H12l-4 3v-3H5Z" />
      <path d="M9 10.5h.01M12 10.5h.01M15 10.5h.01" />
    </svg>
  );
}
