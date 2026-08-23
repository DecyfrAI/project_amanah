import { useCallback, useEffect, useRef, type SyntheticEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { TOUR_STEPS } from './tour-steps';
import { useWorkspaceTour } from './useWorkspaceTour';

import styles from './WorkspaceTour.module.css';

/**
 * Skippable first-visit guide, tucked beside the sidebar.
 *
 * A small solid card, not a page-dimming modal, so the workspace stays
 * readable while the steps run. Completion is stored locally until a profile
 * API owns onboarding_status.
 */
export function WorkspaceTour() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const navigate = useNavigate();
  const {
    isOpen,
    stepIndex,
    stepCount,
    saveFailed,
    closeWithoutSaving,
    skip,
    finish,
    goNext,
    goBack,
  } = useWorkspaceTour();
  const step = TOUR_STEPS[stepIndex];
  const isLast = stepIndex >= stepCount - 1;

  const handleCancel = useCallback(
    (event: SyntheticEvent<HTMLDialogElement>): void => {
      event.preventDefault();
      closeWithoutSaving();
    },
    [closeWithoutSaving],
  );

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog === null) {
      return;
    }
    if (isOpen && !dialog.open) {
      // Non-modal so the dashboard stays usable under the card.
      if (typeof dialog.show === 'function') {
        dialog.show();
      } else {
        dialog.showModal();
      }
    }
    if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || step === undefined) {
      return;
    }
    void navigate(step.to);
  }, [isOpen, navigate, step]);

  if (step === undefined) {
    return null;
  }

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby="workspace-tour-title"
      onCancel={handleCancel}
    >
      <p className={styles.progress}>
        {stepIndex + 1} / {stepCount}
      </p>
      <h2 id="workspace-tour-title" className={styles.title}>
        {step.title}
      </h2>
      <p className={styles.body}>{step.body}</p>

      {saveFailed && (
        <output className={styles.saveError}>
          The tour preference could not be saved in this browser. You can open Tour to see it again.
        </output>
      )}

      <div className={styles.actions}>
        <button type="button" className={styles.skip} onClick={skip}>
          Skip
        </button>
        <div className={styles.arrows}>
          <button
            type="button"
            className={styles.arrow}
            onClick={goBack}
            disabled={stepIndex === 0}
            aria-label="Back"
          >
            <span aria-hidden="true">‹</span>
          </button>
          {isLast ? (
            <button type="button" className={styles.arrow} onClick={finish} aria-label="Finish">
              <span aria-hidden="true">✓</span>
            </button>
          ) : (
            <button type="button" className={styles.arrow} onClick={goNext} aria-label="Next">
              <span aria-hidden="true">›</span>
            </button>
          )}
        </div>
      </div>
    </dialog>
  );
}
