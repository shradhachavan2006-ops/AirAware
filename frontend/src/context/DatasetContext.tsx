/**
 * DatasetContext — global active-dataset state for AirAware V2.
 *
 * All analysis pages read `useDataset().dataset.id` and pass it as
 * `?dataset_id=<id>` to API calls. The context is persisted to
 * localStorage so the user's selection survives page reloads.
 */

import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { DatasetInfo } from '../api';

export const DEFAULT_DATASET_ID = 'demo:pune';
export const DEFAULT_DATASET_NAME = 'Pune (Demo)';

interface DatasetContextValue {
  dataset: DatasetInfo | null;
  setDataset: (d: DatasetInfo) => void;
  isDefault: boolean;
}

const DatasetContext = createContext<DatasetContextValue>({
  dataset: null,
  setDataset: () => {},
  isDefault: true,
});

const STORAGE_KEY = 'airaware_v2_active_dataset';

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [dataset, setDatasetState] = useState<DatasetInfo | null>(null);

  // Restore from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as DatasetInfo;
        if (parsed?.id) setDatasetState(parsed);
      }
    } catch {
      /* ignore corrupt storage */
    }
  }, []);

  function setDataset(d: DatasetInfo) {
    setDatasetState(d);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(d));
    } catch {
      /* ignore quota errors */
    }
  }

  return (
    <DatasetContext.Provider
      value={{
        dataset,
        setDataset,
        isDefault: !dataset || dataset.id === DEFAULT_DATASET_ID,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset() {
  return useContext(DatasetContext);
}

/** Returns the active dataset_id, defaulting to 'demo:pune' if nothing selected. */
export function useDatasetId(): string {
  const { dataset } = useDataset();
  return dataset?.id ?? DEFAULT_DATASET_ID;
}
