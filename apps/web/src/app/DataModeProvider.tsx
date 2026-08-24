import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

import {
  readDataMode,
  readSelectedDataMode,
  selectApiDataMode,
  writeMockDataPreference,
  type DataMode,
} from '@/api';

interface DataModeContextValue {
  readonly mode: DataMode;
  readonly isMockDataEnabled: boolean;
  readonly canUseLiveData: boolean;
  setMockDataEnabled: (isEnabled: boolean) => Promise<void>;
}

const DataModeContext = createContext<DataModeContextValue | null>(null);

/**
 * Owns the viewer's request-source preference without changing authentication.
 * A signed-in live user can therefore inspect synthetic fixtures and return to
 * live reads without replacing or weakening their server-verified session.
 */
export function DataModeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<DataMode>(() => readSelectedDataMode());
  const configuredMode = readDataMode();
  const canUseLiveData = configuredMode !== 'fixture';

  const setMockDataEnabled = useCallback(
    async (isEnabled: boolean): Promise<void> => {
      if (!isEnabled && !canUseLiveData) {
        return;
      }

      const nextMode = isEnabled ? 'fixture' : configuredMode;
      if (nextMode === mode) {
        return;
      }

      await queryClient.cancelQueries();
      writeMockDataPreference(isEnabled);
      selectApiDataMode(nextMode);
      setMode(nextMode);
      await queryClient.resetQueries();
    },
    [canUseLiveData, configuredMode, mode, queryClient],
  );

  const value = useMemo<DataModeContextValue>(
    () => ({
      mode,
      isMockDataEnabled: mode === 'fixture',
      canUseLiveData,
      setMockDataEnabled,
    }),
    [canUseLiveData, mode, setMockDataEnabled],
  );

  return <DataModeContext.Provider value={value}>{children}</DataModeContext.Provider>;
}

export function useDataMode(): DataModeContextValue {
  const value = useContext(DataModeContext);
  if (value === null) {
    throw new Error('useDataMode must be used inside a DataModeProvider');
  }
  return value;
}
