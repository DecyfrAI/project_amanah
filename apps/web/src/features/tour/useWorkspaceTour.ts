import { useCallback, useEffect, useState } from 'react';

import {
  readTourCompletion,
  TOUR_OPEN_EVENT,
  writeTourCompletion,
  type TourCompletion,
} from './tour-storage';
import { TOUR_STEPS } from './tour-steps';

interface UseWorkspaceTourResult {
  readonly isOpen: boolean;
  readonly stepIndex: number;
  readonly stepCount: number;
  readonly saveFailed: boolean;
  readonly open: () => void;
  readonly closeWithoutSaving: () => void;
  readonly skip: () => void;
  readonly finish: () => void;
  readonly goNext: () => void;
  readonly goBack: () => void;
}

/**
 * Owns tour open state, step index, and local persistence.
 *
 * Auto-opens once when no completion is stored. Help / Settings call `open`
 * (or dispatch the open event) to replay without clearing the prior status
 * until the reader Skip/Finish again.
 */
export function useWorkspaceTour(): UseWorkspaceTourResult {
  const [isOpen, setIsOpen] = useState(() => readTourCompletion() === null);
  const [stepIndex, setStepIndex] = useState(0);
  const [saveFailed, setSaveFailed] = useState(false);

  const open = useCallback((): void => {
    setSaveFailed(false);
    setStepIndex(0);
    setIsOpen(true);
  }, []);

  const persist = useCallback((status: TourCompletion): void => {
    const wrote = writeTourCompletion(status);
    setSaveFailed(!wrote);
    setIsOpen(false);
  }, []);

  const skip = useCallback((): void => {
    persist('skipped');
  }, [persist]);

  const finish = useCallback((): void => {
    persist('done');
  }, [persist]);

  const closeWithoutSaving = useCallback((): void => {
    // Escape treats an unfinished auto-tour as a skip so it does not return
    // every refresh; an explicit Help replay that is dismissed also skips.
    persist('skipped');
  }, [persist]);

  const goNext = useCallback((): void => {
    setStepIndex((current) => {
      if (current >= TOUR_STEPS.length - 1) {
        return current;
      }
      return current + 1;
    });
  }, []);

  const goBack = useCallback((): void => {
    setStepIndex((current) => Math.max(0, current - 1));
  }, []);

  useEffect(() => {
    const handleOpen = (): void => {
      open();
    };
    window.addEventListener(TOUR_OPEN_EVENT, handleOpen);
    return () => {
      window.removeEventListener(TOUR_OPEN_EVENT, handleOpen);
    };
  }, [open]);

  return {
    isOpen,
    stepIndex,
    stepCount: TOUR_STEPS.length,
    saveFailed,
    open,
    closeWithoutSaving,
    skip,
    finish,
    goNext,
    goBack,
  };
}
